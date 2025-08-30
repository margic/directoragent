from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional, Any

from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from nats.aio.errors import ErrConnectionClosed, ErrNoServers

from sim_racecenter_agent.logging import get_logger
from ..core.state_cache import StateCache
from ..config.settings import Settings
from ..schemas import validation

_LOGGER = get_logger(__name__)

_LAST_INGESTOR: "NATSIngestor | None" = None  # for diagnostics tools


class NATSIngestor:
    """Ingests NATS live subjects, optional JetStream historical catch-up, and persists chat + snapshots."""

    def __init__(self, cache: StateCache, settings: Settings):
        self.cache = cache
        self.settings = settings
        self.nc: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._stop = asyncio.Event()
        # Chat persistence / DB
        self._chat_task: Optional[asyncio.Task] = None
        self._chat_conn = None  # sqlite3 connection
        self._chat_sub = None  # JetStream pull subscription
        # Chat metrics
        self._chat_pulled = 0
        self._chat_persisted = 0
        self._chat_last_id: Optional[str] = None
        self._chat_last_pull_ts: Optional[float] = None
        self._chat_last_insert_ts: Optional[float] = None
        # Catch-up metrics
        self._catchup_counts: dict[str, int] = {}
        self._catchup_started_ts: Optional[float] = None
        self._catchup_completed_ts: Optional[float] = None
        self._catchup_subject_metrics: dict[str, dict] = {}
        global _LAST_INGESTOR
        _LAST_INGESTOR = self

    # ---------------- Connection -----------------
    async def connect(self):
        nc = NATS()
        opts = {}
        if self.settings.nats.username and self.settings.nats.password:
            opts["user"] = self.settings.nats.username
            opts["password"] = self.settings.nats.password
        await asyncio.wait_for(
            nc.connect(servers=[self.settings.nats.url], **opts),
            timeout=self.settings.nats.connect_timeout,
        )
        self.nc = nc
        try:
            self._js = nc.jetstream()
        except Exception:
            self._js = None
        _LOGGER.info("[nats] connected %s", self.settings.nats.url)

    async def close(self):
        if self.nc:
            try:
                await self.nc.drain()
            except Exception:
                pass
            self.nc = None
        if self._chat_task:
            try:
                await asyncio.wait_for(self._chat_task, timeout=2)
            except Exception:
                pass
            self._chat_task = None
        if self._chat_conn:
            try:
                self._chat_conn.close()
            except Exception:
                pass
            self._chat_conn = None

    def stop(self):
        self._stop.set()

    # ---------------- Persistence DB -----------------
    def _ensure_db(self):
        if self._chat_conn is not None:
            return
        import sqlite3

        path = os.environ.get("SQLITE_PATH", getattr(self.settings, "sqlite_path", "data/agent.db"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._chat_conn = sqlite3.connect(path)
        cur = self._chat_conn.cursor()
        # Chat
        cur.execute(
            "CREATE TABLE IF NOT EXISTS chat_messages( id TEXT PRIMARY KEY, username TEXT, message TEXT, avatar_url TEXT, yt_type TEXT, ts_iso TEXT, ts REAL, day TEXT )"
        )
        cur.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chat_messages_fts USING fts5(message, content='chat_messages', content_rowid='rowid')"
        )
        cur.execute(
            "CREATE TRIGGER IF NOT EXISTS chat_messages_ai AFTER INSERT ON chat_messages BEGIN INSERT INTO chat_messages_fts(rowid, message) VALUES (new.rowid, new.message); END;"
        )
        # Snapshots
        cur.execute("CREATE TABLE IF NOT EXISTS session_snapshots(ts REAL, data TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS session_state_snapshots(ts REAL, data TEXT)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS standings_snapshots(ts REAL, car_idx INT, position INT, car_number TEXT, driver TEXT, last_lap_s REAL, best_lap_s REAL, lap INT, created_at REAL, PRIMARY KEY(ts, car_idx))"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS track_conditions_snapshots(ts REAL PRIMARY KEY, data TEXT)"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_standings_ts ON standings_snapshots(ts)")
        self._chat_conn.commit()

    # ---------------- Handlers -----------------
    async def _handle_telemetry(self, msg):  # pragma: no cover
        try:
            frame = json.loads(msg.data.decode())
        except Exception:
            return
        subset = {
            "driver_id": frame.get("driver_id") or frame.get("display_name"),
            "display_name": frame.get("display_name") or frame.get("driver_id"),
            "CarNumber": frame.get("CarNumber"),
            "CarDistAhead": frame.get("CarDistAhead"),
            "CarDistBehind": frame.get("CarDistBehind"),
            "CarNumberAhead": frame.get("CarNumberAhead"),
            "CarNumberBehind": frame.get("CarNumberBehind"),
            "_emulator": frame.get("_emulator"),
        }
        if subset.get("driver_id"):
            self.cache.upsert_telemetry_frame(subset)

    async def _handle_session(self, msg):  # pragma: no cover
        try:
            data = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.session", data):
            return
        drivers = data.get("drivers") or []
        if drivers:
            self.cache.update_roster(
                [
                    {
                        "driver_id": d.get("UserName") or d.get("CarIdx"),
                        "display_name": d.get("UserName") or d.get("CarIdx"),
                        "CarNumber": d.get("CarNumber"),
                    }
                    for d in drivers
                ]
            )
        try:
            self._ensure_db()
            ts = float(data.get("timestamp") or data.get("ts") or 0.0)
            conn = self._chat_conn
            if conn is not None:
                conn.execute(
                    "INSERT INTO session_snapshots(ts, data) VALUES(?, ?)", (ts, json.dumps(data))
                )
                conn.commit()
        except Exception:
            pass

    async def _handle_session_state(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.session_state", payload):
            return
        self.cache.set_session_state(payload)
        try:
            self._ensure_db()
            ts = float(payload.get("timestamp") or payload.get("ts") or 0.0)
            conn = self._chat_conn
            if conn is not None:
                conn.execute(
                    "INSERT INTO session_state_snapshots(ts, data) VALUES(?, ?)",
                    (ts, json.dumps(payload)),
                )
                conn.commit()
        except Exception:
            pass

    async def _handle_standings(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.standings", payload):
            return
        # Normalize cars list: tests may publish 'pos' instead of 'position'. Cache expects 'car_idx'
        cars_raw = payload.get("cars", []) or []
        norm_cars: list[dict] = []
        for c in cars_raw:
            if not isinstance(c, dict):
                continue
            car_idx = c.get("car_idx")
            if car_idx is None:
                continue
            pos = c.get("position") if c.get("position") is not None else c.get("pos")
            norm = dict(c)
            if pos is not None:
                norm["position"] = pos
            norm_cars.append(norm)
        self.cache.set_standings(payload.get("timestamp", 0.0), norm_cars)
        try:
            self._ensure_db()
            ts = float(payload.get("timestamp") or 0.0)
            cars = norm_cars
            import time as _t

            now = _t.time()
            rows = [
                (
                    ts,
                    c.get("car_idx"),
                    c.get("position") if c.get("position") is not None else c.get("pos"),
                    c.get("car_number"),
                    c.get("driver") or c.get("display_name") or c.get("name"),
                    c.get("last_lap_s"),
                    c.get("best_lap_s"),
                    c.get("lap"),
                    now,
                )
                for c in cars
                if c.get("car_idx") is not None
            ]
            if rows:
                conn = self._chat_conn
                if conn is not None:
                    conn.executemany(
                        "INSERT OR IGNORE INTO standings_snapshots(ts, car_idx, position, car_number, driver, last_lap_s, best_lap_s, lap, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                        rows,
                    )
                    conn.commit()
        except Exception:
            pass

    async def _handle_lap_timing(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.lap_timing", payload):
            return
        self.cache.set_lap_timing(payload.get("timestamp", 0.0), payload.get("cars", []))

    async def _handle_track_conditions(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.track_conditions", payload):
            return
        self.cache.set_track_conditions(payload)
        try:
            self._ensure_db()
            ts = float(payload.get("timestamp") or payload.get("ts") or 0.0)
            conn = self._chat_conn
            if conn is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO track_conditions_snapshots(ts, data) VALUES(?, ?)",
                    (ts, json.dumps(payload)),
                )
                conn.commit()
        except Exception:
            pass

    async def _handle_incident(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.incident", payload):
            return
        self.cache.add_incident_event(payload)

    async def _handle_pit(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.pit", payload):
            return
        self.cache.add_pit_event(payload)

    async def _handle_stint(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if not validation.is_valid("iracing.stint", payload):
            return
        self.cache.update_stint(payload.get("car_idx"), payload)

    async def _handle_chat_passthrough(self, msg):  # pragma: no cover
        # Accept chat messages for real-time UI even if persistence disabled
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            return
        if validation.is_valid("youtube.chat.message", payload):
            self.cache.add_chat_message(payload)

    # ---------------- Chat persistence (JetStream pull) -----------------
    async def _ensure_chat_stream(self):  # pragma: no cover
        if not self._js:
            return
        stream = self.settings.chat_stream
        subject = self.settings.nats.chat_input_subject
        durable = self.settings.chat_durable
        try:
            try:
                # type: ignore[arg-type]
                await self._js.add_stream({"name": stream, "subjects": [subject]})
            except Exception:
                pass
            try:
                await self._js.add_consumer(
                    stream,
                    {  # type: ignore[arg-type]
                        "durable_name": durable,
                        "deliver_policy": "all",
                        "ack_policy": "explicit",
                        "max_ack_pending": 1000,
                    },
                )
            except Exception:
                pass
            if self._chat_sub is None:
                # type: ignore[arg-type]
                self._chat_sub = await self._js.pull_subscribe(
                    subject, durable=durable, stream=stream
                )
        except Exception as e:
            _LOGGER.debug("[chat] ensure stream failed %s", e)

    async def _chat_pull_loop(self):  # pragma: no cover
        assert self._js
        self._ensure_db()
        insert_sql = "INSERT OR IGNORE INTO chat_messages(id, username, message, avatar_url, yt_type, ts_iso, ts, day) VALUES(?,?,?,?,?,?,?,?)"
        batch = max(1, int(self.settings.chat_pull_batch))
        interval = max(0.1, float(self.settings.chat_pull_interval))
        while not self._stop.is_set():
            try:
                if self._chat_sub is None:
                    await self._ensure_chat_stream()
                msgs = []
                if self._chat_sub is not None:
                    # type: ignore[attr-defined]
                    msgs = await self._chat_sub.fetch(batch, timeout=interval)
            except Exception:
                await asyncio.sleep(interval)
                continue
            changed = False
            if msgs:
                import time as _t

                self._chat_pulled += len(msgs)
                self._chat_last_pull_ts = _t.time()
            for m in msgs:
                try:
                    payload = json.loads(m.data.decode())
                    if not validation.is_valid("youtube.chat.message", payload):
                        await m.ack()
                        continue
                    self.cache.add_chat_message(payload)
                    data = payload.get("data") or {}
                    mid = data.get("id")
                    if mid:
                        username = data.get("username")
                        message = data.get("message") or ""
                        avatar = data.get("avatarUrl")
                        yttype = data.get("type")
                        iso_ts = data.get("timestamp")
                        try:
                            dt = (
                                datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
                                if iso_ts
                                else datetime.now(timezone.utc)
                            )
                        except Exception:
                            dt = datetime.now(timezone.utc)
                        epoch = dt.timestamp()
                        day = dt.strftime("%Y-%m-%d")
                        try:
                            conn = self._chat_conn
                            if conn is not None:
                                conn.execute(
                                    insert_sql,
                                    (mid, username, message, avatar, yttype, iso_ts, epoch, day),
                                )
                                # Defensive: ensure FTS row exists even if trigger creation failed earlier
                                try:
                                    conn.execute(
                                        "INSERT INTO chat_messages_fts(rowid, message) SELECT rowid, message FROM chat_messages WHERE id=?",
                                        (mid,),
                                    )
                                except Exception:
                                    pass
                                changed = True
                                self._chat_persisted += 1
                                self._chat_last_id = mid
                                import time as _t

                                self._chat_last_insert_ts = _t.time()
                        except Exception:
                            pass
                    await m.ack()
                except Exception:
                    try:
                        await m.term()
                    except Exception:
                        pass
            if changed:
                conn = self._chat_conn
                if conn is not None:
                    try:
                        conn.commit()
                    except Exception:
                        pass
        conn = self._chat_conn
        if conn is not None:
            try:
                conn.commit()
            except Exception:
                pass

    def chat_persistence_metrics(self) -> dict:
        return {
            "pulled": self._chat_pulled,
            "persisted": self._chat_persisted,
            "last_id": self._chat_last_id,
            "last_pull_ts": self._chat_last_pull_ts,
            "last_insert_ts": self._chat_last_insert_ts,
            "stream": self.settings.chat_stream,
            "durable": self.settings.chat_durable,
            "enabled": self.settings.enable_chat and self.settings.enable_chat_persist,
        }

    # ---------------- JetStream catch-up -----------------
    async def _catchup_jetstream(self):  # pragma: no cover
        if not self._js:
            return
        import time as _t

        self._catchup_started_ts = _t.time()
        subjects = [
            (
                "IRACING_HISTORY",
                self.settings.nats.session_subject,
                True,
                self.settings.catchup_max_session,
                self._handle_session,
            ),
            (
                "IRACING_HISTORY",
                "iracing.session_state",
                self.settings.enable_session_state,
                self.settings.catchup_max_session_state,
                self._handle_session_state,
            ),
            (
                "IRACING_HISTORY",
                "iracing.standings",
                self.settings.enable_extended_standings,
                self.settings.catchup_max_standings,
                self._handle_standings,
            ),
            (
                "IRACING_HISTORY",
                "iracing.lap_timing",
                self.settings.enable_lap_timing,
                self.settings.catchup_max_lap_timing,
                self._handle_lap_timing,
            ),
            (
                "IRACING_HISTORY",
                "iracing.track_conditions",
                self.settings.enable_track_conditions,
                getattr(self.settings, "catchup_max_track_conditions", 3),
                self._handle_track_conditions,
            ),
            (
                "IRACING_HISTORY",
                "iracing.stint",
                self.settings.enable_stint,
                self.settings.catchup_max_stints,
                self._handle_stint,
            ),
            (
                "IRACING_EVENTS",
                "iracing.incident",
                self.settings.enable_incident_events,
                getattr(self.settings, "catchup_max_incidents", 10),
                self._handle_incident,
            ),
            # Chat historical replay (ensure chat stream name may differ; only if persistence enabled and stream configured as history)
            (
                self.settings.chat_stream,
                self.settings.nats.chat_input_subject,
                (self.settings.enable_chat and self.settings.enable_chat_persist),
                getattr(self.settings, "catchup_max_chat", 50),
                self._handle_chat_passthrough,
            ),
        ]

        async def _run_one(stream: str, subject: str, limit: int, handler):
            import time as _t2

            try:
                start = _t2.time()
                before = self._catchup_counts.get(subject, 0)
                await self._replay_last(stream, subject, limit, handler)
                after = self._catchup_counts.get(subject, 0)
                delta = after - before
                end = _t2.time()
                if delta > 0:
                    self._catchup_subject_metrics[subject] = {
                        "count": delta,
                        "duration_s": round(end - start, 6),
                        "start_ts": start,
                        "end_ts": end,
                    }
                    _LOGGER.info(
                        "[catchup] subject=%s replayed=%d total=%d time=%.3fs",
                        subject,
                        delta,
                        sum(self._catchup_counts.values()),
                        end - start,
                    )
            except Exception:
                pass

        tasks = [
            asyncio.create_task(_run_one(s, subj, lim, h))
            for s, subj, en, lim, h in subjects
            if en and lim > 0
        ]
        if tasks:
            await asyncio.gather(*tasks)
        self._catchup_completed_ts = _t.time()
        if self._catchup_counts:
            _LOGGER.info(
                "[catchup] complete subjects=%d total_msgs=%d duration=%.3fs",
                len(self._catchup_counts),
                sum(self._catchup_counts.values()),
                (self._catchup_completed_ts - self._catchup_started_ts)
                if self._catchup_started_ts
                else -1.0,
            )

    async def _replay_last(
        self, stream: str, subject: str, max_msgs: int, handler
    ):  # pragma: no cover
        assert self._js
        try:
            info = await self._js.stream_info(stream)
        except Exception:
            return
        last_seq = getattr(info.state, "last_seq", 0)
        if not last_seq:
            return
        collected: list[Any] = []
        seq = last_seq
        while seq > 0 and len(collected) < max_msgs:
            try:
                msg = await self._js.get_msg(stream_name=stream, seq=seq)
            except Exception:
                break
            if msg.subject == subject:
                collected.append(msg)
            seq -= 1
        for m in reversed(collected):

            class _Wrap:
                def __init__(self, data: bytes):
                    self.data = data

            # Use handler (updates cache) AND persist if chat subject
            await handler(_Wrap(m.data))
            if subject == self.settings.nats.chat_input_subject:
                try:
                    payload = json.loads(m.data.decode())
                    if validation.is_valid("youtube.chat.message", payload):
                        data = payload.get("data") or {}
                        mid = data.get("id")
                        if mid:
                            username = data.get("username")
                            message = data.get("message") or ""
                            avatar = data.get("avatarUrl")
                            yttype = data.get("type")
                            iso_ts = data.get("timestamp")
                            try:
                                dt = (
                                    datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
                                    if iso_ts
                                    else datetime.now(timezone.utc)
                                )
                            except Exception:
                                dt = datetime.now(timezone.utc)
                            epoch = dt.timestamp()
                            day = dt.strftime("%Y-%m-%d")
                            self._ensure_db()
                            conn = self._chat_conn
                            if conn is not None:
                                try:
                                    conn.execute(
                                        "INSERT OR IGNORE INTO chat_messages(id, username, message, avatar_url, yt_type, ts_iso, ts, day) VALUES(?,?,?,?,?,?,?,?)",
                                        (
                                            mid,
                                            username,
                                            message,
                                            avatar,
                                            yttype,
                                            iso_ts,
                                            epoch,
                                            day,
                                        ),
                                    )
                                    try:
                                        conn.execute(
                                            "INSERT INTO chat_messages_fts(rowid, message) SELECT rowid, message FROM chat_messages WHERE id=?",
                                            (mid,),
                                        )
                                    except Exception:
                                        pass
                                    conn.commit()
                                    self._chat_persisted += 1
                                    self._chat_last_id = mid
                                except Exception:
                                    pass
                except Exception:
                    pass
            # Best-effort ack if this is a JetStream Msg instance with ack() method
            try:  # pragma: no cover
                if hasattr(m, "ack"):
                    await m.ack()
            except Exception:
                pass
        if collected:
            self._catchup_counts[subject] = self._catchup_counts.get(subject, 0) + len(collected)

    def catchup_metrics(self) -> dict:
        import time as _t

        now = _t.time()
        return {
            "counts": dict(self._catchup_counts),
            "total": sum(self._catchup_counts.values()),
            "started_ts": self._catchup_started_ts,
            "completed_ts": self._catchup_completed_ts,
            "duration_s": (self._catchup_completed_ts - self._catchup_started_ts)
            if self._catchup_started_ts and self._catchup_completed_ts
            else None,
            "age_s": (now - self._catchup_completed_ts) if self._catchup_completed_ts else None,
            "subjects": self._catchup_subject_metrics,
        }

    # ---------------- Run loop -----------------
    async def run(self):  # pragma: no cover
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self.connect()
                assert self.nc
                if self.settings.enable_jetstream_catchup:
                    try:
                        await self._catchup_jetstream()
                    except Exception:
                        pass
                # Live subscriptions
                await self.nc.subscribe(
                    self.settings.nats.telemetry_subject, cb=self._handle_telemetry
                )
                await self.nc.subscribe(self.settings.nats.session_subject, cb=self._handle_session)
                if self.settings.enable_extended_standings:
                    await self.nc.subscribe("iracing.standings", cb=self._handle_standings)
                if self.settings.enable_lap_timing:
                    await self.nc.subscribe("iracing.lap_timing", cb=self._handle_lap_timing)
                if self.settings.enable_session_state:
                    await self.nc.subscribe("iracing.session_state", cb=self._handle_session_state)
                if self.settings.enable_incident_events:
                    await self.nc.subscribe("iracing.incident", cb=self._handle_incident)
                if self.settings.enable_pit_events:
                    await self.nc.subscribe("iracing.pit", cb=self._handle_pit)
                if self.settings.enable_track_conditions:
                    await self.nc.subscribe(
                        "iracing.track_conditions", cb=self._handle_track_conditions
                    )
                if self.settings.enable_stint:
                    await self.nc.subscribe("iracing.stint", cb=self._handle_stint)
                if self.settings.enable_chat and self.settings.nats.chat_input_subject:
                    await self.nc.subscribe(
                        self.settings.nats.chat_input_subject, cb=self._handle_chat_passthrough
                    )
                # Chat persistence
                if self.settings.enable_chat and self.settings.enable_chat_persist:
                    self._ensure_db()
                    if self._chat_task is None:
                        _LOGGER.info("[chat] starting persistence loop")
                        self._chat_task = asyncio.create_task(self._chat_pull_loop())
                backoff = 1.0
                await self._stop.wait()
            except (ErrConnectionClosed, ErrNoServers, asyncio.CancelledError):
                if self._stop.is_set():
                    break
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            finally:
                await self.close()


async def run_telemetry_listener(
    cache: StateCache, settings: Settings, stop_event: asyncio.Event
):  # pragma: no cover
    ing = NATSIngestor(cache, settings)
    task = asyncio.create_task(ing.run())
    try:
        await stop_event.wait()
    finally:
        ing.stop()
        await asyncio.sleep(0)
        try:
            await asyncio.wait_for(task, timeout=5)
        except asyncio.TimeoutError:
            pass

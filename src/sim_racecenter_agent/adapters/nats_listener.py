from __future__ import annotations
from __future__ import annotations
import asyncio
import json
import os
from typing import Optional, Any
from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from nats.aio.errors import ErrConnectionClosed, ErrNoServers
from ..core.state_cache import StateCache
from ..config.settings import Settings
from ..schemas import validation

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


class NATSIngestor:
    def __init__(self, cache: StateCache, settings: Settings):
        self.cache = cache
        self.settings = settings
        self.nc: Optional[NATS] = None
        self._stop = asyncio.Event()
        self._js: Optional[JetStreamContext] = None

    async def connect(self):
        nc = NATS()
        url = self.settings.nats.url
        opts = {}
        if self.settings.nats.username and self.settings.nats.password:
            opts["user"] = self.settings.nats.username
            opts["password"] = self.settings.nats.password
        await nc.connect(servers=[url], **opts)
        self.nc = nc
        try:
            self._js = nc.jetstream()
        except Exception:
            self._js = None
        if LOG_LEVEL in {"DEBUG", "INFO"}:
            print(f"[nats] connected {url}")

    async def close(self):
        if self.nc:
            try:
                await self.nc.drain()
            except Exception:
                pass
            self.nc = None

    # ---- Handlers ----
    async def _handle_telemetry(self, msg):  # pragma: no cover
        try:
            frame = json.loads(msg.data.decode())
            if LOG_LEVEL == "DEBUG":
                print(f"[nats] telemetry: {frame}")
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad telemetry json")
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
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad session json")
            return
        if not validation.is_valid("iracing.session", data):
            if LOG_LEVEL == "DEBUG":
                print("[nats] invalid session payload")
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

    async def _handle_standings(self, msg):  # pragma: no cover
        try:
            if LOG_LEVEL == "DEBUG":
                print(f"[nats] msg: {msg.data.decode()}")
            payload = json.loads(msg.data.decode())
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad standings json")
            return
        if not validation.is_valid("iracing.standings", payload):
            return
        self.cache.set_standings(payload.get("timestamp", 0.0), payload.get("cars", []))

    async def _handle_lap_timing(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad lap_timing json")
            return
        if not validation.is_valid("iracing.lap_timing", payload):
            return
        self.cache.set_lap_timing(payload.get("timestamp", 0.0), payload.get("cars", []))

    async def _handle_session_state(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad session_state json")
            return
        if not validation.is_valid("iracing.session_state", payload):
            return
        self.cache.set_session_state(payload)

    async def _handle_incident(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad incident json")
            return
        if not validation.is_valid("iracing.incident", payload):
            return
        self.cache.add_incident_event(payload)

    async def _handle_pit(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad pit json")
            return
        if not validation.is_valid("iracing.pit", payload):
            return
        self.cache.add_pit_event(payload)

    async def _handle_track_conditions(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad track_conditions json")
            return
        if not validation.is_valid("iracing.track_conditions", payload):
            return
        self.cache.set_track_conditions(payload)

    async def _handle_stint(self, msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            if LOG_LEVEL == "DEBUG":
                print("[nats] bad stint json")
            return
        if not validation.is_valid("iracing.stint", payload):
            return
        self.cache.update_stint(payload.get("car_idx"), payload)

    # ---- Run Loop ----
    async def run(self):
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self.connect()
                assert self.nc
                if self.settings.enable_jetstream_catchup:
                    try:
                        await self._catchup_jetstream()
                    except Exception as e:  # pragma: no cover
                        if LOG_LEVEL in {"DEBUG", "INFO"}:
                            print(f"[nats] catch-up error {e}")
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
                backoff = 1.0
                await self._stop.wait()
            except (ErrConnectionClosed, ErrNoServers, asyncio.CancelledError):
                if self._stop.is_set():
                    break
                if LOG_LEVEL in {"DEBUG", "INFO"}:
                    print(f"[nats] reconnect in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            except Exception as e:  # pragma: no cover
                if LOG_LEVEL in {"DEBUG", "INFO"}:
                    print(f"[nats] error {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            finally:
                await self.close()

    def stop(self):
        self._stop.set()

    # ---- JetStream Catch-up ----
    async def _catchup_jetstream(self):  # pragma: no cover
        if not self._js:
            return
        subjects = [
            (
                "IRACING_EVENTS",
                "iracing.incident",
                self.settings.enable_incident_events,
                self.settings.catchup_max_incidents,
                self._handle_incident,
            ),
            (
                "IRACING_EVENTS",
                "iracing.pit",
                self.settings.enable_pit_events,
                self.settings.catchup_max_pits,
                self._handle_pit,
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
                "iracing.stint",
                self.settings.enable_stint,
                self.settings.catchup_max_stints,
                self._handle_stint,
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
                self.settings.nats.session_subject,
                True,
                self.settings.catchup_max_session,
                self._handle_session,
            ),
        ]
        for stream, subject, enabled, limit, handler in subjects:
            if not enabled or limit <= 0:
                continue
            try:
                await self._replay_last(stream, subject, limit, handler)
            except Exception as e:
                if LOG_LEVEL == "DEBUG":
                    print(f"[nats] catch-up failed for {subject}: {e}")

    async def _replay_last(self, stream: str, subject: str, max_msgs: int, handler):
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

            await handler(_Wrap(m.data))


async def run_telemetry_listener(cache: StateCache, settings: Settings, stop_event: asyncio.Event):
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

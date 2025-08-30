from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Optional

from nats.aio.client import Client as NATS

from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.director.agent import DirectorAgent
from sim_racecenter_agent.logging import get_logger

_LOGGER = get_logger("chat_responder")


class ChatResponder:
    """Subscribe to chat, generate answers, publish responses (stdio MCP only)."""

    def __init__(self, trigger_prefix: Optional[str] = None):
        self.settings = get_settings()
        self.trigger_prefix = trigger_prefix
        self.nc: NATS | None = None
        self.agent = DirectorAgent()
        self._stop = asyncio.Event()
        self._auth_violation_count = 0  # track repeated auth failures
        ignore_raw = os.environ.get("RESPONDER_IGNORE_USERNAMES", "Sim RaceCenter")
        self.ignore_usernames = {u.strip().lower() for u in ignore_raw.split(",") if u.strip()}
        # Queue + stats
        import time as _t

        self._queue: asyncio.Queue[dict] = asyncio.Queue(
            maxsize=int(os.environ.get("CHAT_QUEUE_MAXSIZE", "100"))
        )
        self._worker_task: asyncio.Task | None = None
        self._stats = {
            "received": 0,
            "enqueued": 0,
            "processed": 0,
            "dropped": 0,
            "last_answer_time": 0.0,
            "start_time": _t.time(),
        }
        self._stats_every = max(1, int(os.environ.get("CHAT_STATS_EVERY", "10")))

    async def connect(self):
        if self.nc:
            return
        self.nc = NATS()
        nats_settings = self.settings.nats
        opts: dict = {}
        if nats_settings.username and nats_settings.password:
            _LOGGER.debug("Using NATS credentials user=%s", nats_settings.username)
            opts["user"] = nats_settings.username
            opts["password"] = nats_settings.password
        else:
            _LOGGER.debug("No NATS credentials provided (connecting anonymously)")
        import os as _os  # local import for diag
        import traceback as _tb

        _LOGGER.debug(
            "[chat_responder] attempting connect url=%s env.NATS_URL=%s",
            nats_settings.url,
            _os.environ.get("NATS_URL"),
        )
        if "127.0.0.1" in nats_settings.url or "localhost" in nats_settings.url:
            _LOGGER.warning(
                "[chat_responder] WARNING loopback URL stack:\n%s",
                "".join(_tb.format_stack(limit=8)),
            )

        # Diagnostic callbacks
        async def _error_cb(e):  # pragma: no cover
            msg = str(e)
            _LOGGER.error("NATS error callback: %s", msg)
            if "Authorization Violation" in msg:
                self._auth_violation_count += 1
                failfast = os.environ.get("NATS_FAILFAST_AUTH", "1") == "1"
                max_violations = int(os.environ.get("NATS_MAX_AUTH_VIOLATIONS", "3"))
                if failfast and self._auth_violation_count >= max_violations:
                    _LOGGER.error(
                        "NATS authorization failed %d times (max=%d) - exiting early. Set NATS_USERNAME/NATS_PASSWORD or relax server auth. Disable with NATS_FAILFAST_AUTH=0",
                        self._auth_violation_count,
                        max_violations,
                    )
                    # Trigger shutdown sequence
                    try:
                        self.stop()
                    except Exception:
                        pass

        async def _closed_cb():  # pragma: no cover
            _LOGGER.warning("NATS connection closed")

        async def _disconnected_cb():  # pragma: no cover
            _LOGGER.warning("NATS disconnected")

        async def _reconnected_cb():  # pragma: no cover
            _LOGGER.info("NATS reconnected")

        opts.update(
            {
                "error_cb": _error_cb,
                "closed_cb": _closed_cb,
                "disconnected_cb": _disconnected_cb,
                "reconnected_cb": _reconnected_cb,
                "max_reconnect_attempts": 3,
                "reconnect_time_wait": 2,
            }
        )
        try:
            await self.nc.connect(servers=[nats_settings.url], **opts)
        except Exception as e:
            if "Authorization Violation" in str(e):
                _LOGGER.error(
                    "NATS authorization failure (url=%s user=%s) - check credentials or server auth config",
                    nats_settings.url,
                    nats_settings.username,
                )
            raise
        pool = []
        try:  # pragma: no cover
            pool = [getattr(s, "uri", str(s)) for s in getattr(self.nc, "_server_pool", [])]
        except Exception:
            pass
        _LOGGER.info("Connected NATS %s server_pool=%s", nats_settings.url, pool)

    async def close(self):
        if self.nc:
            try:
                await self.nc.drain()
            except Exception:
                pass
            self.nc = None
        # Also close underlying director agent (MCP client)
        try:
            await self.agent.close()
        except Exception:
            pass

    async def _handle_chat(self, msg):  # pragma: no cover
        verbose = os.environ.get("CHAT_LOG_VERBOSE") == "1"
        raw_bytes = msg.data
        try:
            payload = json.loads(raw_bytes.decode())
        except Exception:
            _LOGGER.debug("Bad chat JSON payload=%r", raw_bytes[:200])
            self._stats["dropped"] += 1
            return
        if verbose:
            _LOGGER.debug("Raw chat payload: %s", payload)
        if not isinstance(payload, dict):
            if verbose:
                _LOGGER.debug("Ignoring non-dict payload")
            self._stats["dropped"] += 1
            return
        if payload.get("type") != "youtube_chat_message":
            if verbose:
                _LOGGER.debug("Ignoring payload type=%r", payload.get("type"))
            self._stats["dropped"] += 1
            return
        data = payload.get("data") or {}
        message_text = (data.get("message") or "").strip()
        if not message_text:
            if verbose:
                _LOGGER.debug("Empty message text in payload id=%r", data.get("id"))
            self._stats["dropped"] += 1
            return
        if self.trigger_prefix and not message_text.startswith(self.trigger_prefix):
            if verbose:
                _LOGGER.debug(
                    "Message %r does not start with trigger prefix %r",
                    message_text,
                    self.trigger_prefix,
                )
            self._stats["dropped"] += 1
            return
        if self.trigger_prefix:
            message_text = message_text[len(self.trigger_prefix) :].lstrip()
        username = (data.get("username") or "unknown").strip()
        mid = data.get("id") or ""
        if username.lower() in self.ignore_usernames:
            if verbose:
                _LOGGER.debug("Ignoring message from ignored username: %s", username)
            self._stats["dropped"] += 1
            return
        self._stats["received"] += 1
        item = {
            "id": mid,
            "username": username,
            "message": message_text,
            "ts_recv": time.time(),
        }
        if self._queue.full():
            self._stats["dropped"] += 1
            _LOGGER.warning(
                "Chat queue full (size=%d max=%d) dropping id=%s",
                self._queue.qsize(),
                self._queue.maxsize,
                mid,
            )
            return
        try:
            self._queue.put_nowait(item)
            self._stats["enqueued"] += 1
            _LOGGER.info(
                "Chat message enqueued id=%s user=%s qsize=%d", mid, username, self._queue.qsize()
            )
        except Exception:
            self._stats["dropped"] += 1
            _LOGGER.exception("Failed to enqueue chat message id=%s", mid)

    async def _worker(self):  # pragma: no cover
        while not self._stop.is_set() or not self._queue.empty():
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            mid = item["id"]
            username = item["username"]
            message_text = item["message"]
            _LOGGER.info(
                "Processing chat id=%s user=%s q_remaining=%d", mid, username, self._queue.qsize()
            )
            answer = None
            started = time.time()
            timeout_s = float(os.environ.get("CHAT_WORKER_ANSWER_TIMEOUT", "25"))
            try:
                try:
                    answer = await asyncio.wait_for(
                        self.agent.answer(message_text), timeout=timeout_s
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        "Answer generation timeout id=%s after %.1fs (dropping message)",
                        mid,
                        timeout_s,
                    )
                except Exception as e:
                    _LOGGER.error("Answer generation failed id=%s: %s", mid, e, exc_info=True)
            finally:
                dur = time.time() - started
                slow_thresh = float(os.environ.get("CHAT_SLOW_THRESHOLD", "5"))
                if dur >= slow_thresh:
                    _LOGGER.info(
                        "Chat processing duration id=%s user=%s duration=%.2fs slow>=%.2fs",
                        mid,
                        username,
                        dur,
                        slow_thresh,
                    )
            if answer:
                out = {
                    "type": "director_answer",
                    "data": {
                        "input_id": mid,
                        "username": username,
                        "question": message_text,
                        "answer": answer,
                        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "ts": time.time(),
                    },
                }
                try:
                    assert self.nc
                    await self.nc.publish(
                        self.settings.nats.chat_response_subject, json.dumps(out).encode()
                    )
                    self._stats["last_answer_time"] = time.time()
                    _LOGGER.info("Published answer for %s", mid)
                except Exception as e:
                    _LOGGER.error("Publish failed id=%s: %s", mid, e)
            else:
                _LOGGER.debug("No answer for id=%s", mid)
            self._stats["processed"] += 1
            # Periodic stats log
            if self._stats["processed"] % self._stats_every == 0:
                import math
                import time as _t

                uptime = _t.time() - self._stats["start_time"]
                _LOGGER.info(
                    "[chat_stats] recv=%d enq=%d proc=%d drop=%d qsize=%d uptime=%.1fs last_answer_age=%.1fs",
                    self._stats["received"],
                    self._stats["enqueued"],
                    self._stats["processed"],
                    self._stats["dropped"],
                    self._queue.qsize(),
                    uptime,
                    (_t.time() - self._stats["last_answer_time"])
                    if self._stats["last_answer_time"]
                    else math.nan,
                )
            self._queue.task_done()

    async def run(self):
        await self.connect()
        assert self.nc
        # Subscribe FIRST so external readiness check succeeds quickly
        subj = self.settings.nats.chat_input_subject
        _LOGGER.info(
            "ChatResponder starting subscription subject=%s ignored_users=%s trigger_prefix=%r",
            subj,
            sorted(self.ignore_usernames),
            self.trigger_prefix,
        )
        # Use a queue group so multiple responders (future) share load and flush to activate
        await self.nc.subscribe(subj, queue="director_chat", cb=self._handle_chat)
        try:  # ensure subscription processed server-side
            await self.nc.flush(timeout=2)
        except Exception:
            pass
        _LOGGER.info(
            "Subscribed chat subject %s -> responses %s",
            subj,
            self.settings.nats.chat_response_subject,
        )

        # Kick off prewarm asynchronously AFTER subscription so readiness isn't delayed
        async def _prewarm():  # pragma: no cover
            prewarm_flag = os.environ.get("CHAT_PREWARM_MCP", "1") == "1"
            if not prewarm_flag:
                return
            try:
                start_t = time.time()
                tools = await self.agent.prewarm()
                _LOGGER.info(
                    "MCP/Gemini prewarm complete tools=%d in %.2fs", tools, time.time() - start_t
                )
            except Exception as e:
                _LOGGER.warning("MCP prewarm failed: %s", e)

        asyncio.create_task(_prewarm(), name="mcp_prewarm")
        # Start worker
        self._worker_task = asyncio.create_task(self._worker(), name="chat_worker")
        await self._stop.wait()

    def stop(self):
        self._stop.set()
        # Put sentinel to unblock queue retrieval
        try:
            self._queue.put_nowait({"id": "__stop__", "username": "system", "message": ""})
        except Exception:
            pass


async def run_standalone():  # pragma: no cover
    prefix = os.environ.get("CHAT_TRIGGER_PREFIX")
    responder = ChatResponder(trigger_prefix=prefix)
    task = asyncio.create_task(responder.run())
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        responder.stop()
    finally:
        await responder.close()
        try:
            await asyncio.wait_for(task, timeout=5)
        except asyncio.TimeoutError:
            pass

#!/usr/bin/env python
"""Agent process: NATS ingestion + chat responder (LLM planning) using MCP tools.

Uses FastMCP stdio transport exclusively. Requires GEMINI_API_KEY for real LLM
planning (else fallback heuristics if forced via env).
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import os

from sim_racecenter_agent.logging import configure_logging, get_logger
from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.core.state_cache import StateCache
from sim_racecenter_agent.adapters.nats_listener import run_telemetry_listener
from sim_racecenter_agent.director.chat_responder import ChatResponder

configure_logging()
LOG = get_logger("run_agent")


async def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description="Run Sim RaceCenter agent")
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print resolved settings (including NATS URL) and exit",
    )
    parser.add_argument(
        "--grace-timeout",
        type=float,
        default=8.0,
        help="Seconds to wait for graceful shutdown before force cancelling tasks (default 8)",
    )
    args = parser.parse_args()
    settings = get_settings()

    if args.print_config:
        # Minimal settings dump for troubleshooting environment issues
        dump = {
            "nats_url": settings.nats.url,
            "telemetry_subject": settings.nats.telemetry_subject,
            "session_subject": settings.nats.session_subject,
            "chat_input_subject": settings.nats.chat_input_subject,
            "chat_response_subject": settings.nats.chat_response_subject,
            "embedding_model": settings.embedding_model,
            "sqlite_path": settings.sqlite_path,
        }
        import json as _json

        print(_json.dumps(dump, indent=2))
        return

    # stdio-only: no configuration needed beyond optional MCP_SERVER_CMD
    cache = StateCache(settings.snapshot_pos_history, settings.incident_ring_size)
    stop_event = asyncio.Event()
    import os as _os

    # Ingestion enable/disable (new: ENABLE_INGEST=1|0 ; legacy: DISABLE_INGEST=1)
    env_enable = _os.getenv("ENABLE_INGEST")
    if env_enable is not None:
        ingest_enabled = env_enable not in {"0", "false", "False"}
    else:  # fallback legacy flag
        legacy_disable = _os.getenv("DISABLE_INGEST", "0") == "1"
        ingest_enabled = not legacy_disable
        if "DISABLE_INGEST" in _os.environ:
            LOG.warning(
                "DISABLE_INGEST is deprecated; use ENABLE_INGEST=1 (default) or ENABLE_INGEST=0 to disable"
            )
    run_telemetry = _os.getenv("RUN_TELEMETRY_LISTENER") not in {"0", "false", "False"}
    telemetry_task = None
    if (not ingest_enabled) or (not run_telemetry):
        LOG.info(
            "Telemetry listener disabled (ingest_enabled=%s RUN_TELEMETRY_LISTENER=%s)",
            ingest_enabled,
            run_telemetry,
        )
    else:
        telemetry_task = asyncio.create_task(
            run_telemetry_listener(cache, settings, stop_event), name="telemetry_listener"
        )
    responder = None
    responder_task = None
    if os.getenv("DISABLE_CHAT_RESPONDER") not in {"1", "true", "True"}:
        responder = ChatResponder()
        responder_task = asyncio.create_task(responder.run(), name="chat_responder")
    else:
        LOG.info("ChatResponder disabled via DISABLE_CHAT_RESPONDER=1")

    LOG.info(
        "Agent started (MCP stdio mode) NATS_URL=%s env.NATS_URL=%s ingest_enabled=%s telemetry=%s session=%s chat_in=%s chat_out=%s ignored_users=%s",
        settings.nats.url,
        _os.environ.get("NATS_URL"),
        ingest_enabled,
        settings.nats.telemetry_subject,
        settings.nats.session_subject,
        settings.nats.chat_input_subject,
        settings.nats.chat_response_subject,
        getattr(responder, "ignore_usernames", set()),
    )
    # --- Signal Handling ---
    shutting_down = False
    force = False

    def _signal_handler(sig, _frame):  # type: ignore[override]
        nonlocal shutting_down, force
        if not shutting_down:
            shutting_down = True
            LOG.info("Signal %s received: initiating graceful shutdown", sig)
            stop_event.set()
            if responder:
                responder.stop()
        else:
            force = True
            LOG.warning("Second signal %s received: force cancellation", sig)

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            # type: ignore[arg-type]
            loop.add_signal_handler(s, _signal_handler, s, None)
        except NotImplementedError:  # pragma: no cover (platforms without signal support)
            signal.signal(s, _signal_handler)

    # Optional auto-stop for tests (e.g., AGENT_AUTO_STOP_SECONDS=2)
    auto_stop = os.getenv("AGENT_AUTO_STOP_SECONDS")
    if auto_stop:
        try:
            delay = float(auto_stop)
            if delay > 0:

                async def _auto():  # pragma: no cover
                    await asyncio.sleep(delay)
                    if not stop_event.is_set():
                        LOG.info("Auto-stop after %.2fs (AGENT_AUTO_STOP_SECONDS)", delay)
                        stop_event.set()
                        if responder:
                            responder.stop()

                asyncio.create_task(_auto(), name="auto_stop")
        except Exception:
            LOG.warning("Invalid AGENT_AUTO_STOP_SECONDS=%r", auto_stop)

    try:
        # Wait directly on the stop event instead of long sleep; this allows quick signal handling.
        await stop_event.wait()
    finally:
        # Phase 1: graceful
        stop_event.set()
        if responder:
            responder.stop()
            await responder.close()
        grace = args.grace_timeout
        pending = [t for t in (telemetry_task, responder_task) if t is not None]
        for t in list(pending):
            if t.done():
                continue
            try:
                await asyncio.wait_for(t, timeout=grace)
            except asyncio.TimeoutError:
                LOG.warning("Task %s did not finish in %.1fs, cancelling", t.get_name(), grace)
                t.cancel()
        # Phase 2: force cancel if still running
        for t in list(pending):
            if not t.done():
                try:
                    await asyncio.wait_for(t, timeout=2)
                except asyncio.TimeoutError:
                    LOG.error("Task %s still pending after force cancel", t.get_name())
        LOG.info("Shutdown complete")


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())

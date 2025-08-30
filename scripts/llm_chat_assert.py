#!/usr/bin/env python
"""End-to-end Gemini tool-call assertion (direct Gemini integration).

Spawns the agent (run_agent.py), publishes a chat message to the NATS chat input
subject, and asserts that Gemini tool session started and an answer was
published.

Success criteria (exit 0):
    - See line containing: "starting Gemini tool session" (lazy cold start)
    - See line containing: "Published answer for" (chat response emitted)

Failure (exit 1):
  - Timeout before lines appear, or agent exits early, or NATS publish fails.

Prerequisites:
  - NATS server reachable at settings.nats.url (env NATS_URL overrides)
  - GEMINI_API_KEY set (else the agent will take fallback path and lines will not appear)
  - Do NOT set FORCE_FALLBACK_HEURISTICS=1

Optional env:
  - TEST_MESSAGE: override default chat test message
  - ASSERT_TIMEOUT: total seconds (default 60)
  - STARTUP_TIMEOUT: seconds to wait for subscription readiness (default 25)
  - LOG_LEVEL (overrides to INFO if unset)

Usage:
  GEMINI_API_KEY=realkey python scripts/llm_chat_assert.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import sys
import time

from sim_racecenter_agent.config.settings import get_settings

SESSION_START_RE = re.compile(r"starting Gemini tool session")
ANSWER_PUB_RE = re.compile(r"Published answer for")


async def _read_stream(stream, buf: list[str]):  # type: ignore[annotation-unchecked]
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode(errors="replace").rstrip()
        buf.append(text)
        # Echo to our stdout for transparency
        print(text)


async def publish_chat(message: str):
    from nats.aio.client import Client as NATS

    settings = get_settings()
    subj = settings.nats.chat_input_subject
    nc = NATS()
    connect_opts = {}
    if settings.nats.username and settings.nats.password:
        connect_opts["user"] = settings.nats.username
        connect_opts["password"] = settings.nats.password
    await nc.connect(servers=[settings.nats.url], **connect_opts)
    payload = {
        "type": "youtube_chat_message",
        "data": {
            "id": f"assert-{int(time.time() * 1000)}",
            "username": "LLMTester",
            "message": message,
        },
    }
    await nc.publish(subj, json.dumps(payload).encode())
    await nc.flush()
    await nc.drain()


async def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("[assert] GEMINI_API_KEY missing: cannot assert Gemini tool path", file=sys.stderr)
        return 2

    total_timeout = float(os.environ.get("ASSERT_TIMEOUT", "60"))
    startup_timeout = float(os.environ.get("STARTUP_TIMEOUT", "25"))
    test_message = os.environ.get("TEST_MESSAGE", "show closest battle now")

    env = dict(os.environ)
    env.setdefault("LOG_LEVEL", "INFO")
    # Ensure chat stats don't spam quickly during check
    env.setdefault("CHAT_STATS_EVERY", "999")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "scripts/run_agent.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    lines: list[str] = []
    reader_task = asyncio.create_task(_read_stream(proc.stdout, lines))  # type: ignore[arg-type]

    # Wait for subscription readiness or timeout
    start = time.time()
    ready = False
    while time.time() - start < startup_timeout:
        await asyncio.sleep(0.5)
        if any("ChatResponder starting subscription" in ln for ln in lines) and any(
            "Subscribed chat subject" in ln for ln in lines
        ):
            ready = True
            break
        # Detect repeating auth failures quickly
        if any("Authorization Violation" in ln for ln in lines[-10:]):
            print(
                "[assert] Detected NATS Authorization Violation in agent logs. Ensure NATS_USERNAME/NATS_PASSWORD env vars are set and valid (or server permits anonymous).",
                file=sys.stderr,
            )
            try:
                proc.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass
            await asyncio.wait_for(reader_task, timeout=5)
            return 1
        if proc.returncode is not None:
            break

    if not ready:
        print(
            "[assert] Did not observe subscription readiness lines within startup timeout",
            file=sys.stderr,
        )
        try:
            proc.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
        await asyncio.wait_for(reader_task, timeout=5)
        return 1

    # Publish chat message
    try:
        await publish_chat(test_message)
    except Exception as e:
        print(f"[assert] Failed to publish chat message: {e}", file=sys.stderr)
        proc.send_signal(signal.SIGINT)
        await asyncio.wait_for(reader_task, timeout=5)
        return 1

    # Wait for Gemini session start + published answer
    deadline = time.time() + total_timeout
    session_seen = False
    published_seen = False
    while time.time() < deadline and (not session_seen or not published_seen):
        await asyncio.sleep(0.5)
        for ln in lines[-200:]:  # recent slice
            if not session_seen and SESSION_START_RE.search(ln):
                session_seen = True
            if not published_seen and ANSWER_PUB_RE.search(ln):
                published_seen = True
        if proc.returncode is not None:
            break

    # Trigger shutdown
    try:
        proc.send_signal(signal.SIGINT)
    except ProcessLookupError:
        pass

    # Give up to 10s for graceful exit
    try:
        await asyncio.wait_for(proc.wait(), timeout=10)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    try:
        await asyncio.wait_for(reader_task, timeout=5)
    except asyncio.TimeoutError:
        reader_task.cancel()

    if session_seen and published_seen:
        print("[assert] PASS: Gemini session + published answer detected")
        return 0
    else:
        if not session_seen:
            print("[assert] FAIL: Gemini tool session start log not detected", file=sys.stderr)
        if not published_seen:
            print("[assert] FAIL: Published answer log not detected", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    try:
        rc = asyncio.run(main())
    except KeyboardInterrupt:
        rc = 130
    sys.exit(rc)

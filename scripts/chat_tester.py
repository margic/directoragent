#!/usr/bin/env python
"""Minimal chat tester using project settings for NATS config.

Run:
    python scripts/chat_tester.py

Environment overrides (same as app): NATS_URL, NATS_USERNAME, NATS_PASSWORD,
CHAT_INPUT_SUBJECT, CHAT_RESPONSE_SUBJECT. Optional CHAT_TESTER_USERNAME.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

from nats.aio.client import Client as NATS

try:
    from sim_racecenter_agent.config.settings import get_settings
    from sim_racecenter_agent.logging import get_logger
except Exception:  # pragma: no cover
    print("Failed to import project modules; ensure PYTHONPATH includes src/", file=sys.stderr)
    raise

LOGGER = get_logger("chat_tester")


async def run():
    settings = get_settings()
    nats_cfg = settings.nats
    nats_url = nats_cfg.url
    input_subject = nats_cfg.chat_input_subject
    response_subject = nats_cfg.chat_response_subject

    nc = NATS()
    connect_opts = {}
    if nats_cfg.username and nats_cfg.password:
        connect_opts["user"] = nats_cfg.username
        connect_opts["password"] = nats_cfg.password
    await nc.connect(servers=[nats_url], **connect_opts)
    LOGGER.info(
        "Connected NATS %s (input=%s response=%s)", nats_url, input_subject, response_subject
    )

    # Subscribe to response subject first
    async def _on_response(msg):  # pragma: no cover (interactive)
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            LOGGER.debug("Non-JSON response: %r", msg.data[:100])
            return
        kind = payload.get("type")
        data = payload.get("data") or {}
        if kind == "director_answer":
            print(
                f"[RESPONSE] answer='{data.get('answer', '')}' question='{data.get('question', '')}' id={data.get('input_id')}"
            )
        else:
            print(f"[RESPONSE RAW] {json.dumps(payload)[:300]}")

    await nc.subscribe(response_subject, cb=_on_response)
    LOGGER.info(
        "Subscribed response subject %s; sending messages to %s", response_subject, input_subject
    )

    username = os.environ.get("CHAT_TESTER_USERNAME", "Tester")
    print(
        f"Enter chat messages as '{username}'. Blank line or Ctrl+C to exit."
        f" (Subjects: in={input_subject} out={response_subject})"
    )
    loop = asyncio.get_event_loop()

    while True:
        try:
            msg = await loop.run_in_executor(None, sys.stdin.readline)
        except KeyboardInterrupt:
            break
        if msg is None or msg.strip() == "":
            break
        text = msg.rstrip("\n")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
            "type": "youtube_chat_message",
            "data": {
                "id": str(uuid.uuid4()),
                "username": username,
                "message": text,
                "avatarUrl": None,
                "timestamp": now,
                "type": "chat",
            },
        }
        await nc.publish(input_subject, json.dumps(payload).encode())
        LOGGER.info("Published chat message len=%d", len(text))
        await nc.flush(timeout=2)
        await asyncio.sleep(0.1)

    LOGGER.info("Exiting chat tester")
    await nc.drain()


def main():  # pragma: no cover
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    main()

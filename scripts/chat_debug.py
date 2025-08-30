#!/usr/bin/env python
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from nats.aio.client import Client as NATS
from sim_racecenter_agent.logging import configure_logging, get_logger
from sim_racecenter_agent.config.settings import get_settings

configure_logging()
LOG = get_logger("chat_debug")


async def main():
    settings = get_settings()
    url = settings.nats.url
    subj_in = settings.nats.chat_input_subject
    subj_out = settings.nats.chat_response_subject
    nc = NATS()
    await nc.connect(servers=[url])
    got_response = asyncio.Event()

    async def _resp(msg):  # pragma: no cover
        try:
            payload = json.loads(msg.data.decode())
        except Exception:
            LOG.error("Bad response JSON: %r", msg.data[:120])
            return
        LOG.info("Received director response: %s", payload)
        got_response.set()

    await nc.subscribe(subj_out, cb=_resp)
    mid = str(uuid.uuid4())
    username = os.environ.get("CHAT_TEST_USER", "TestUser")
    message = os.environ.get("CHAT_TEST_MESSAGE", "battle for the lead?")
    payload = {
        "type": "youtube_chat_message",
        "data": {
            "id": mid,
            "username": username,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }
    await nc.publish(subj_in, json.dumps(payload).encode())
    LOG.info("Published test chat message id=%s user=%s subj=%s", mid, username, subj_in)
    try:
        await asyncio.wait_for(got_response.wait(), timeout=8)
    except asyncio.TimeoutError:
        LOG.error("No response received on %s within timeout", subj_out)
    await nc.drain()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())

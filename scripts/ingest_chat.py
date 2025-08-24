#!/usr/bin/env python
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timezone

from nats.aio.client import Client as NATS
from nats.js.api import DeliverPolicy

SQLITE_PATH = os.environ.get("SQLITE_PATH", "data/agent.db")
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
SUBJECT = os.environ.get("CHAT_SUBJECT", "youtube.chat.message")
DURABLE = os.environ.get("CHAT_DURABLE", "director_chat")
STREAM = os.environ.get("CHAT_STREAM", "CHAT")
BATCH = int(os.environ.get("CHAT_PULL_BATCH", "100"))
PULL_INTERVAL = float(os.environ.get("CHAT_PULL_INTERVAL", "0.5"))

INSERT_SQL = """
INSERT OR IGNORE INTO chat_messages(id, username, message, avatar_url, yt_type, ts_iso, ts, day)
VALUES(?,?,?,?,?,?,?,?)
"""


class ChatIngestor:
    def __init__(self):
        self.conn = sqlite3.connect(SQLITE_PATH)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA temp_store=MEMORY;")

    def close(self):
        self.conn.close()

    def upsert_message(self, payload: dict):
        if payload.get("type") != "youtube_chat_message":
            return False
        data = payload.get("data") or {}
        mid = data.get("id")
        if not mid:
            return False
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
        self.conn.execute(INSERT_SQL, (mid, username, message, avatar, yttype, iso_ts, epoch, day))
        return True

    def commit(self):
        self.conn.commit()


async def run():
    ingestor = ChatIngestor()
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    js = nc.jetstream()

    # Ensure stream exists (optional create if absent)
    try:
        await js.stream_info(STREAM)
    except Exception:
        await js.add_stream(name=STREAM, subjects=[SUBJECT])

    # Prepare durable consumer (pull based)
    try:
        await js.consumer_info(STREAM, DURABLE)
    except Exception:
        await js.add_consumer(
            stream=STREAM,
            config={
                "durable_name": DURABLE,
                "deliver_policy": DeliverPolicy.All.value,
                "ack_policy": "explicit",
                "ack_wait": 30_000_000_000,  # 30s
                "max_ack_pending": 1000,
            },
        )

    print(f"Ingesting from {SUBJECT} durable={DURABLE} stream={STREAM}")
    try:
        while True:
            msgs = []
            try:
                msgs = await js.pull(STREAM, DURABLE, batch=BATCH, timeout=PULL_INTERVAL)
            except Exception:
                # timeout / no messages
                await asyncio.sleep(PULL_INTERVAL)
            changed = False
            for m in msgs:
                try:
                    payload = json.loads(m.data.decode())
                    if ingestor.upsert_message(payload):
                        changed = True
                    await m.ack()
                except Exception as e:
                    print(f"Error processing message: {e}")
                    await m.term()
            if changed:
                ingestor.commit()
    finally:
        ingestor.close()
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(run())

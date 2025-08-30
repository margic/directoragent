from __future__ import annotations

import time

SCHEMA_VERSION = 2


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def add_meta(payload: dict) -> dict:
    payload.setdefault("generated_at", utc_now())
    payload.setdefault("schema_version", SCHEMA_VERSION)
    return payload

from __future__ import annotations

import time

from ...core.state_cache import StateCache


def build_get_live_snapshot_tool(cache: StateCache):
    def handler(args: dict) -> dict:
        return {
            "schema_version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session": {
                "id": getattr(cache.session_meta, "id", None),
                "lap": getattr(cache.session_meta, "lap", None),
                "flag": getattr(cache.session_meta, "flag", None),
            },
            "leaderboard": cache.snapshot_leaderboard(),
            "versions": cache.versions,
        }

    return {
        "name": "get_live_snapshot",
        "description": "Return current session + leaderboard snapshot",
        "input_schema": {"type": "object", "properties": {}},
        "output_schema": {"type": "object"},
        "handler": handler,
    }

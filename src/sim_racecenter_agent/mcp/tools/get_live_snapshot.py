from __future__ import annotations

import time

from ...core.state_cache import StateCache


def build_get_live_snapshot_tool(cache: StateCache):
    def handler(args: dict) -> dict:
        sess_state = cache.session_state() or {}
        tc = cache.track_conditions() or {}
        standings = cache.standings()
        return {
            "schema_version": 2,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_state": sess_state,
            "track_conditions": tc,
            "standings_top": standings[:15],
            "leaderboard": cache.snapshot_leaderboard(),  # backward compatible
            "lap_timing_top": cache.lap_timing()[:15],
            "incidents_recent": cache.recent_incidents(20),
            "pits_recent": cache.recent_pits(20),
            "roster_size": len(cache.roster()),
            "drivers_preview": [
                {"CarIdx": d.get("CarIdx"), "car": d.get("CarNumber"), "name": d.get("UserName")}
                for d in cache.roster()[:5]
            ],
        }

    return {
        "name": "get_live_snapshot",
        "description": "Return current composite live snapshot (standings, session, timing, events)",
        "input_schema": {"type": "object", "properties": {}},
        "output_schema": {"type": "object"},
        "handler": handler,
    }

from __future__ import annotations

from typing import Any, Dict
import time

from ...core.state_cache import StateCache


def build_get_session_history_tool(cache: StateCache):
    """Return recent session_state messages (most recent last)."""

    def _handler(args: Dict[str, Any]):
        limit = args.get("limit", 5)
        try:
            limit = int(limit)
        except Exception:
            limit = 5
        limit = max(1, min(limit, 50))
        history = cache.session_state_history(limit)
        return {
            "schema_version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "count": len(history),
            "items": history,
        }

    return {
        "name": "get_session_history",
        "description": "Return recent session state updates (latest last).",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": [],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "items": {"type": "array", "items": {"type": "object"}},
            },
        },
        "handler": _handler,
    }

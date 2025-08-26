from __future__ import annotations

import time
from typing import Any, Dict

from ...core.state_cache import StateCache


def build_get_roster_tool(cache: StateCache):
    def handler(args: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - trivial
        drivers = cache.roster()
        # Normalize keys exposed
        out = [
            {
                "CarIdx": d.get("CarIdx"),
                "car": d.get("CarNumber"),
                "name": d.get("UserName") or d.get("display_name"),
            }
            for d in drivers
        ]
        return {
            "schema_version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "count": len(out),
            "drivers": out,
        }

    return {
        "name": "get_roster",
        "description": "Return full current session roster (CarIdx, car number, name)",
        "input_schema": {"type": "object", "properties": {}},
        "output_schema": {"type": "object"},
        "handler": handler,
    }

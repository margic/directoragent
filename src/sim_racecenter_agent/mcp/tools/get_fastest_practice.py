from __future__ import annotations

# Tool: get_fastest_practice
# Select the fastest driver in the current (practice) session based on best lap time when
# available (lap_timing snapshot). Falls back to standings last_lap_s if lap timing not present.

import time
from typing import Any, Dict, List

from ...core.state_cache import StateCache


def build_get_fastest_practice_tool(cache: StateCache):
    def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        top_n = int(args.get("top_n", 5))
        lap_timing = cache.lap_timing()
        standings = cache.standings()
        roster = cache.roster()
        # Build car_idx -> (car_number, name) mapping
        num_name: Dict[int, Dict[str, Any]] = {}
        for d in roster:
            idx = d.get("CarIdx")
            if isinstance(idx, int):
                num_name[idx] = {
                    "car_number": d.get("CarNumber"),
                    "name": d.get("UserName") or d.get("display_name") or d.get("driver_id"),
                }
        # Use lap_timing priority
        records: List[Dict[str, Any]] = []
        source = "lap_timing" if lap_timing else "standings"
        if lap_timing:
            for r in lap_timing:
                car_idx = r.get("car_idx")
                if not isinstance(car_idx, int):
                    continue
                best = r.get("best_lap_s")
                last = r.get("last_lap_s")
                lap = r.get("lap")
                # Exclude sentinel / invalid values (None, <=0, negative lap index)
                if best is None or not isinstance(best, (int, float)) or best <= 0:
                    continue
                if isinstance(lap, (int, float)) and lap < 0:
                    continue
                enriched = {
                    "car_idx": car_idx,
                    "best_lap_s": best,
                    "last_lap_s": last,
                    "lap": lap,
                }
                enriched.update(num_name.get(car_idx, {}))
                # Add gap to current provisional fastest later
                records.append(enriched)
            records.sort(key=lambda x: x.get("best_lap_s", 9e9))
        else:
            # Fallback: derive "best" from last_lap_s standings if present
            for s in standings:
                car_idx = s.get("car_idx")
                if not isinstance(car_idx, int):
                    continue
                last = s.get("last_lap_s")
                if last is None or not isinstance(last, (int, float)) or last <= 0:
                    continue
                enriched = {
                    "car_idx": car_idx,
                    "best_lap_s": last,
                    "last_lap_s": last,
                    "lap": s.get("lap"),
                }
                enriched.update(num_name.get(car_idx, {}))
                records.append(enriched)
            records.sort(key=lambda x: x.get("best_lap_s", 9e9))
        if not records:
            return {
                "schema_version": 1,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": source,
                "fastest": None,
                "top_n": [],
                "message": "No lap timing data yet.",
            }
        fastest_time = records[0]["best_lap_s"]
        for r in records:
            if r.get("best_lap_s") is not None and fastest_time is not None:
                r["gap_fastest_s"] = round(r["best_lap_s"] - fastest_time, 3)
        return {
            "schema_version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": source,
            "fastest": records[0],
            "top_n": records[:top_n],
            "count": len(records),
        }

    return {
        "name": "get_fastest_practice",
        "description": "Return fastest practice lap (best_lap_s) and top N cars.",
        "input_schema": {
            "type": "object",
            "properties": {"top_n": {"type": "integer", "minimum": 1, "maximum": 50}},
            "required": [],
        },
        "output_schema": {"type": "object"},
        "handler": handler,
    }

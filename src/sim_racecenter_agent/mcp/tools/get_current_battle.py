from __future__ import annotations

import time
from typing import Dict

from ...core.state_cache import StateCache


def build_get_current_battle_tool(cache: StateCache):
    def handler(args: dict) -> dict:
        top_n = int(args.get("top_n_pairs", 1))
        max_dist = float(args.get("max_distance_m", 50.0))
        frames = cache.telemetry_frames()
        pairs: Dict[tuple[str, str], dict] = {}
        emulator_any = False
        for fr in frames:
            car = fr.get("CarNumber")
            if not car:
                continue
            emulator_any = emulator_any or bool(fr.get("_emulator"))
            # ahead relation
            dist_a = fr.get("CarDistAhead")
            car_a = fr.get("CarNumberAhead")
            if isinstance(dist_a, (int, float)) and dist_a > 0 and car_a:
                c1, c2 = sorted([str(car), str(car_a)])
                key = (c1, c2)
                prev = pairs.get(key)
                if dist_a <= max_dist and (prev is None or dist_a < prev["distance_m"]):
                    pairs[key] = {
                        "focus_car": str(car),
                        "other_car": str(car_a),
                        "distance_m": float(dist_a),
                        "relation": "ahead",
                        "driver": fr.get("display_name"),
                        "other_driver": None,
                    }
            # behind relation
            dist_b = fr.get("CarDistBehind")
            car_b = fr.get("CarNumberBehind")
            if isinstance(dist_b, (int, float)) and dist_b > 0 and car_b:
                c1, c2 = sorted([str(car), str(car_b)])
                key = (c1, c2)
                prev = pairs.get(key)
                if dist_b <= max_dist and (prev is None or dist_b < prev["distance_m"]):
                    pairs[key] = {
                        "focus_car": str(car),
                        "other_car": str(car_b),
                        "distance_m": float(dist_b),
                        "relation": "behind",
                        "driver": fr.get("display_name"),
                        "other_driver": None,
                    }
        # attempt to fill other_driver names by lookup
        name_by_car = {
            str(fr.get("CarNumber")): fr.get("display_name") for fr in frames if fr.get("CarNumber")
        }
        pair_list = list(pairs.values())
        for p in pair_list:
            p["other_driver"] = name_by_car.get(p["other_car"]) or p["other_driver"]
        pair_list.sort(key=lambda x: x["distance_m"])
        pair_list = pair_list[:top_n]
        return {
            "schema_version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pairs": pair_list,
            "roster_size": len(cache.roster()),
            "emulator": bool(emulator_any),
            "top_n_requested": top_n,
            "max_distance_m": max_dist,
        }

    return {
        "name": "get_current_battle",
        "description": "Return closest driver pair(s) within distance threshold (proximity battle)",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n_pairs": {"type": "integer", "minimum": 1, "default": 1},
                "max_distance_m": {"type": "number", "minimum": 1, "default": 50.0},
            },
        },
        "output_schema": {"type": "object"},
        "handler": handler,
    }

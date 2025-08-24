import math

from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.core.state_cache import StateCache
from sim_racecenter_agent.mcp.tools.get_current_battle import build_get_current_battle_tool


def make_cache():
    s = get_settings()
    cache = StateCache(s.snapshot_pos_history, s.incident_ring_size)
    return cache


def test_battle_no_data():
    cache = make_cache()
    tool_def = build_get_current_battle_tool(cache)
    out = tool_def["handler"]({})
    assert out["pairs"] == []
    assert out["roster_size"] == 0


def test_battle_single_pair():
    cache = make_cache()
    # simulate roster
    cache.update_roster(
        [
            {"driver_id": "A", "display_name": "Driver A", "CarNumber": "11"},
            {"driver_id": "B", "display_name": "Driver B", "CarNumber": "22"},
        ]
    )
    cache.upsert_telemetry_frame(
        {
            "driver_id": "A",
            "display_name": "Driver A",
            "CarNumber": "11",
            "CarDistAhead": 9.2,
            "CarNumberAhead": "22",
            "CarDistBehind": 0.0,
            "CarNumberBehind": None,
        }
    )
    cache.upsert_telemetry_frame(
        {
            "driver_id": "B",
            "display_name": "Driver B",
            "CarNumber": "22",
            "CarDistBehind": 9.2,
            "CarNumberBehind": "11",
        }
    )
    tool_def = build_get_current_battle_tool(cache)
    out = tool_def["handler"]({"top_n_pairs": 1})
    assert len(out["pairs"]) == 1
    pair = out["pairs"][0]
    assert {pair["focus_car"], pair["other_car"]} == {"11", "22"}
    assert math.isclose(pair["distance_m"], 9.2, rel_tol=1e-3)
    assert out["roster_size"] == 2


def test_battle_threshold_filter():
    cache = make_cache()
    cache.update_roster(
        [
            {"driver_id": "A", "display_name": "Driver A", "CarNumber": "11"},
            {"driver_id": "B", "display_name": "Driver B", "CarNumber": "22"},
        ]
    )
    cache.upsert_telemetry_frame(
        {
            "driver_id": "A",
            "display_name": "Driver A",
            "CarNumber": "11",
            "CarDistAhead": 120.0,
            "CarNumberAhead": "22",
        }
    )
    cache.upsert_telemetry_frame(
        {
            "driver_id": "B",
            "display_name": "Driver B",
            "CarNumber": "22",
            "CarDistBehind": 120.0,
            "CarNumberBehind": "11",
        }
    )
    tool_def = build_get_current_battle_tool(cache)
    out = tool_def["handler"]({"max_distance_m": 50})
    assert out["pairs"] == []

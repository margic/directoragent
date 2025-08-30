from sim_racecenter_agent.core.state_cache import StateCache


def test_cache_initialization_empty():
    cache = StateCache(100, 10)
    assert cache.roster() == []
    assert cache.telemetry_frames() == []
    assert cache.standings() == []
    assert cache.lap_timing() == []
    assert cache.session_state() is None
    assert cache.session_state_history() == []


def test_cache_upserts_and_history():
    cache = StateCache(100, 10)
    cache.update_roster(
        [
            {"CarIdx": 1, "CarNumber": "10", "UserName": "Alice"},
            {"CarIdx": 2, "CarNumber": "22", "UserName": "Bob"},
        ]
    )
    cache.upsert_telemetry_frame(
        {"driver_id": "alice", "CarIdx": 1, "CarNumber": "10", "display_name": "Alice"}
    )
    cache.set_session_state({"flag": "green"})
    cache.set_standings(1.0, [{"car_idx": 1, "pos": 1, "gap_leader_s": 0.0, "last_lap_s": 75.5}])
    lb = cache.snapshot_leaderboard()
    assert len(lb) == 1
    assert lb[0]["pos"] == 1
    # History retains at least one
    hist = cache.session_state_history(5)
    assert hist and hist[-1]["flag"] == "green"

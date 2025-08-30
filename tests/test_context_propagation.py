import pytest

from sim_racecenter_agent.mcp.client_wrapper import MCPToolClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_context_propagation_mutation_and_snapshot(monkeypatch):
    monkeypatch.setenv("ENABLE_INGEST", "0")  # deterministic disable
    monkeypatch.setenv("TEST_ENABLE_MUTATE", "1")
    client = MCPToolClient()
    await client.start()
    tools = await client.list_tools()
    names = {t["name"] for t in tools}
    assert "set_mock_state" in names, "test mutation tool not registered"
    # Inject mock state
    roster = [
        {"CarIdx": 1, "CarNumber": "01", "UserName": "Alice"},
        {"CarIdx": 2, "CarNumber": "02", "UserName": "Bob"},
    ]
    standings = [
        {"car_idx": 1, "pos": 1, "gap_leader_s": 0.0, "last_lap_s": 75.5},
        {"car_idx": 2, "pos": 2, "gap_leader_s": 1.2, "last_lap_s": 76.7},
    ]
    resp = await client.call_tool("set_mock_state", {"roster": roster, "standings": standings})
    assert resp.get("ok") is True
    # Now call live snapshot tool; should reflect injected roster size
    snap = await client.call_tool("get_live_snapshot")
    assert snap.get("roster_size") == 2, f"Unexpected roster_size {snap.get('roster_size')}"
    lb = snap.get("leaderboard") or []
    assert lb and lb[0].get("pos") == 1, "Leaderboard not derived from injected standings"
    await client.close()

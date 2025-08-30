import pytest
from sim_racecenter_agent.director.agent import DirectorAgent


class _FakeGemini:
    def __init__(self, tool_returns):
        self._started = True
        self._tool_returns = tool_returns

    async def ensure_started(self):  # pragma: no cover
        self._started = True

    async def ask(self, prompt: str):
        # Deterministic synthesis mimicking prior expectations using tool outputs
        battle = self._tool_returns.get("get_current_battle", {})
        pairs = battle.get("pairs") or []
        if not pairs:
            return "No close on-track battles at the moment."
        first = pairs[0]
        dist = first.get("distance_m")
        try:
            dist_fmt = f"{float(dist):.1f}m" if dist is not None else "?m"
        except Exception:
            dist_fmt = "?m"
        return f"Car {first.get('focus_car')} vs {first.get('other_car')} gap {dist_fmt}"


class DummyAgent(DirectorAgent):
    def __init__(self):
        super().__init__()
        self._tool_returns: dict[str, dict] = {}
        # Replace Gemini session with fake deterministic generator
        from sim_racecenter_agent.director import agent as _agent_mod  # noqa: F401

        self._gemini = _FakeGemini(self._tool_returns)  # type: ignore[attr-defined]

    def set_tool(self, name: str, result: dict):
        self._tool_returns[name] = result


@pytest.mark.asyncio
async def test_battle_answer():
    ag = DummyAgent()
    ag.set_tool(
        "get_live_snapshot",
        {
            "standings_top": [
                {"car_idx": 1, "pos": 1, "gap_ahead_s": 0, "gap_leader_s": 0},
                {"car_idx": 2, "pos": 2, "gap_ahead_s": 0.5, "gap_leader_s": 0.5},
            ]
        },
    )
    ag.set_tool(
        "get_current_battle",
        {
            "pairs": [{"focus_car": "11", "other_car": "22", "distance_m": 8.44}],
            "max_distance_m": 50,
            "roster_size": 2,
        },
    )
    resp = await ag.answer("Any close battles?")
    assert resp is not None and "Car 11 vs 22" in resp
    assert "8.4m" in resp


@pytest.mark.asyncio
async def test_battle_no_pairs():
    ag = DummyAgent()
    ag.set_tool(
        "get_live_snapshot",
        {"standings_top": [{"car_idx": 1, "pos": 1, "gap_ahead_s": 0, "gap_leader_s": 0}]},
    )
    ag.set_tool("get_current_battle", {"pairs": [], "max_distance_m": 50, "roster_size": 3})
    resp = await ag.answer("closest battle?")
    assert resp is not None and resp.startswith("No close on-track battles")

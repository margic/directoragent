import pytest

from sim_racecenter_agent.director.agent import DirectorAgent


class DummyAgent(DirectorAgent):
    def __init__(self):
        super().__init__(mcp_base_url="http://test")
        self._tool_returns = {}

    def set_tool(self, name, result):
        self._tool_returns[name] = result

    async def _call_tool(self, name: str, arguments: dict):
        return self._tool_returns[name]


@pytest.mark.asyncio
async def test_battle_answer():
    ag = DummyAgent()
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
    assert "8.4m" in resp  # rounded formatting


@pytest.mark.asyncio
async def test_battle_no_pairs():
    ag = DummyAgent()
    ag.set_tool("get_current_battle", {"pairs": [], "max_distance_m": 50, "roster_size": 3})
    resp = await ag.answer("closest battle?")
    assert resp is not None and resp.startswith("No close battles")

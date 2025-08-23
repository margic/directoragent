from __future__ import annotations
import httpx
from ..core.intent import classify_intent

class DirectorAgent:
    def __init__(self, mcp_base_url: str):
        self._mcp_base_url = mcp_base_url.rstrip("/")

    async def answer(self, message: str) -> str | None:
        intent = classify_intent(message)
        if intent == "LEADER":
            snapshot = await self._call_tool("get_live_snapshot", {})
            lb = snapshot.get("leaderboard", [])
            if not lb:
                return "No data yet."
            leader = lb[0]
            return f"Leader: {leader.get('name')} (Car {leader.get('car')}), gap to P2 {lb[1].get('gap') if len(lb)>1 else '—'}"
        return None

    async def _call_tool(self, name: str, arguments: dict):
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(f"{self._mcp_base_url}/mcp/call_tool", json={"name": name, "arguments": arguments})
            resp.raise_for_status()
            return resp.json()["result"]
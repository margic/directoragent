from __future__ import annotations
import httpx
from .reasoning import plan_tools, synthesize_answer


class DirectorAgent:
    def __init__(self, mcp_base_url: str):
        self._mcp_base_url = mcp_base_url.rstrip("/")

    async def answer(self, message: str) -> str | None:
        """Plan and answer using the LLM (single operational mode)."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                tools_resp = await client.get(f"{self._mcp_base_url}/mcp/list_tools")
                tools_resp.raise_for_status()
                tools_meta = tools_resp.json().get("tools") or []
        except Exception:
            return None
        plan = await plan_tools(message, tools_meta)
        if not plan:
            return None
        results: dict[str, dict] = {}
        for step in plan:
            name = step.get("name")
            if not name:
                continue
            args = step.get("arguments") or {}
            try:
                results[name] = await self._call_tool(name, args)
            except Exception:
                results[name] = {"error": "tool_failed"}
        answer = await synthesize_answer(message, results)
        return answer[:200] if answer else None

    async def _call_tool(self, name: str, arguments: dict):
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{self._mcp_base_url}/mcp/call_tool", json={"name": name, "arguments": arguments}
            )
            resp.raise_for_status()
            return resp.json()["result"]

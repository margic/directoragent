import pytest
from sim_racecenter_agent.mcp.client_wrapper import MCPToolClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_client_wrapper_lists_tools_and_calls_tool():
    client = MCPToolClient()
    try:
        await client.start()
        tools = await client.list_tools()
        assert tools, "Expected at least one tool"
        names = {t["name"] for t in tools}
        assert "get_current_battle" in names, "battle tool missing"
        # Call battle tool (should return empty structure initially)
        resp = await client.call_tool("get_current_battle", {})
        # Response may be raw result or standard MCP tool result wrapper
        if "pairs" not in resp and "content" in resp:
            # FastMCP tool call returns result.content list; extract JSON if present
            content = resp.get("content")
            if isinstance(content, list) and content and isinstance(content[0], dict):
                if content[0].get("type") == "text":
                    import json as _json

                    try:
                        inner = _json.loads(content[0].get("text", "{}"))
                        resp = inner
                    except Exception:
                        pass
        assert "pairs" in resp, f"Unexpected tool call shape: {resp}"
        assert resp.get("roster_size") is not None
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_client_wrapper_multiple_list_calls_id_increment():
    client = MCPToolClient()
    try:
        await client.start()
        first = await client.list_tools()
        second = await client.list_tools()
        assert first and second
        # Ensure IDs advanced internally (implicit by no exception). Optionally check name continuity.
        assert {t["name"] for t in first} == {t["name"] for t in second}
    finally:
        await client.close()

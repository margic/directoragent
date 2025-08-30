import pytest

from sim_racecenter_agent.mcp.sdk_server import mcp


@pytest.mark.asyncio
async def test_sdk_server_list_and_battle_empty():
    assert mcp is not None
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "get_current_battle" in names, f"Tool not registered; tools = {names}"
    # Call via FastMCP API; may return TextContent wrapper list
    raw = await mcp.call_tool("get_current_battle", {})
    if (
        isinstance(raw, list) and raw and getattr(raw[0], "type", None) == "text"
    ):  # TextContent list
        import json as _json

        result = _json.loads(raw[0].text)  # type: ignore[attr-defined]
    else:
        result = raw
    assert isinstance(result, dict)
    assert "pairs" in result and isinstance(result["pairs"], list)
    assert result.get("roster_size") == 0

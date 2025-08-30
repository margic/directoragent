import pytest

from sim_racecenter_agent.mcp.sdk_server import mcp


@pytest.mark.asyncio
async def test_tool_catalog_names():
    # mcp._tools is internal; use list_tools through a lightweight client session if available
    # For brevity, introspect the FastMCP instance registry directly.
    expected = {
        "get_live_snapshot",
        "get_current_battle",
        "get_fastest_practice",
        "search_corpus",
        "search_chat",
        "get_roster",
        "get_session_history",
    }
    assert mcp is not None
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    missing = expected - names
    assert not missing, f"Missing tools: {missing}"

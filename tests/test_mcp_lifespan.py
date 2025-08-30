import pytest

from sim_racecenter_agent.mcp.client_wrapper import MCPToolClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_client_start_and_shutdown(monkeypatch):
    # Disable ingestion to keep test deterministic & fast
    # disable ingestion deterministically
    monkeypatch.setenv("ENABLE_INGEST", "0")
    client = MCPToolClient()
    await client.start()
    tools = await client.list_tools()
    assert tools, "No tools listed after start"
    await client.close()

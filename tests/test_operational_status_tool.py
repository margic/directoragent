import os
import pytest
from sim_racecenter_agent.mcp.client_wrapper import MCPToolClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_operational_status_basic():
    # deterministic: disable listener
    os.environ.setdefault("DISABLE_INGEST", "1")
    client = MCPToolClient()
    try:
        await client.start()
        tools = await client.list_tools()
        names = {t.get("name") for t in tools if isinstance(t, dict)}
        assert "get_operational_status" in names
        result = await client.call_tool("get_operational_status", {})
        assert isinstance(result, dict)
        telem = result.get("telemetry_ingest") or {}
        assert "enabled" in telem and "running" in telem
        assert "cache" in result
        cache = result["cache"]
        assert all(k in cache for k in ("roster_size", "lap_timing_records", "standings_records"))
        assert "uptime_s" in result
    finally:
        await client.close()

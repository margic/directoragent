# Sim RaceCenter Agent

Agent + MCP layer for Sim RaceCenter: exposes race domain data (via NATS JetStream + SQLite) to LLM tooling and powers a Director chat responder.

## Quick Start (Dev Container)

1. Clone repo and open in VS Code
2. Reopen in container when prompted
3. Initialize DB (placeholder)

## MCP Transports

Two surfaces:

1. HTTP (FastAPI): `python -m sim_racecenter_agent.mcp.server` (endpoints `/mcp/list_tools`, `/mcp/call_tool`).
2. Stdio JSON-RPC: `python scripts/mcp_stdio.py`.

### Manual stdio usage

```
echo '{"jsonrpc":"2.0","id":1,"method":"list_tools"}' | python scripts/mcp_stdio.py
echo '{"jsonrpc":"2.0","id":2,"method":"call_tool","params":{"name":"get_current_battle","arguments":{}}}' | python scripts/mcp_stdio.py
```

### VS Code Copilot Chat (experimental)

Add to settings.json:
```json
{
  "copilot.experimental.mcpServers": {
    "racecenter": {
      "command": "python",
      "args": ["scripts/mcp_stdio.py"],
      "transport": "stdio"
    }
  }
}
```
Then in Copilot Chat ask: Any close battles?

### Seed test data (interactive shell)

```
from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.core.state_cache import StateCache
from sim_racecenter_agent.mcp.tools.get_current_battle import build_get_current_battle_tool
from sim_racecenter_agent.mcp.registry import tool_registry
s=get_settings(); cache=StateCache(s.snapshot_pos_history,s.incident_ring_size)
tool_registry.register(**build_get_current_battle_tool(cache))
cache.update_roster([
  {"driver_id":"A","display_name":"Driver A","CarNumber":"11"},
  {"driver_id":"B","display_name":"Driver B","CarNumber":"22"},
])
cache.upsert_telemetry_frame({"driver_id":"A","display_name":"Driver A","CarNumber":"11","CarDistAhead":9.2,"CarNumberAhead":"22"})
cache.upsert_telemetry_frame({"driver_id":"B","display_name":"Driver B","CarNumber":"22","CarDistBehind":9.2,"CarNumberBehind":"11"})
print(tool_registry.call("get_current_battle", {"top_n_pairs":1}))
```

#!/usr/bin/env python
"""MCP stdio server for Sim RaceCenter Agent.

Implements a minimal JSON-RPC 2.0 loop over stdin/stdout with two methods:
- list_tools
- call_tool (params: name:str, arguments:dict)

This mirrors the HTTP tool surface but uses stdio transport (better for local Copilot integration).
"""

from __future__ import annotations

import json
import sys
import traceback

from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.core.state_cache import StateCache
from sim_racecenter_agent.mcp.registry import tool_registry
from sim_racecenter_agent.mcp.tools.get_current_battle import build_get_current_battle_tool
from sim_racecenter_agent.mcp.tools.get_live_snapshot import build_get_live_snapshot_tool
from sim_racecenter_agent.mcp.tools.search_corpus import build_search_corpus_tool

# Initialize cache & register tools (same as HTTP server bootstrap)
settings = get_settings()
cache = StateCache(settings.snapshot_pos_history, settings.incident_ring_size)
for tool_def in [
    build_get_live_snapshot_tool(cache),
    build_search_corpus_tool(),
    build_get_current_battle_tool(cache),
]:
    tool_registry.register(
        name=tool_def["name"],
        description=tool_def["description"],
        input_schema=tool_def["input_schema"],
        output_schema=tool_def["output_schema"],
        handler=tool_def["handler"],
    )


# Helper: write JSON-RPC response
def send(obj: dict):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


# Optional notification utility
def notify(method: str, params: dict | None = None):
    send({"jsonrpc": "2.0", "method": method, "params": params or {}})


# Main loop
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
    except Exception as e:
        send({"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {e}"}})
        continue

    _id = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    try:
        if method == "list_tools":
            result = {"tools": tool_registry.list_tools()}
            send({"jsonrpc": "2.0", "id": _id, "result": result})
        elif method == "call_tool":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str):
                raise ValueError("Missing or invalid 'name'")
            res = tool_registry.call(name, arguments)
            send({"jsonrpc": "2.0", "id": _id, "result": res})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": _id, "result": {"pong": True}})
        else:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": _id,
                    "error": {"code": -32601, "message": "Method not found"},
                }
            )
    except Exception as e:
        tb = traceback.format_exc(limit=2)
        send(
            {"jsonrpc": "2.0", "id": _id, "error": {"code": -32000, "message": str(e), "data": tb}}
        )

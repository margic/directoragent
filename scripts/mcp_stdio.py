#!/usr/bin/env python
"""Model Context Protocol (MCP) stdio server for Sim RaceCenter Agent.

Implements a subset of the MCP spec over JSON-RPC 2.0 on stdin/stdout.

Supported methods:
  initialize            -> capability negotiation
  tools/list            -> enumerate registered tools
  tools/call            -> invoke a tool by name with arguments
  ping                  -> simple health probe (non-spec convenience)

Tool call response shape follows MCP: { content: [ { type: "json", value: <tool_result> } ] }
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from typing import Any, Dict

from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.core.state_cache import StateCache


class _ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(
        self, name: str, description: str, input_schema: dict, output_schema: dict, handler
    ):
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "handler": handler,
        }

    def list_tools(self):
        return [{k: v for k, v in t.items() if k != "handler"} for t in self._tools.values()]

    def call(self, name: str, arguments: dict):
        if name not in self._tools:
            raise ValueError(f"Unknown tool '{name}'")
        return self._tools[name]["handler"](arguments)


tool_registry = _ToolRegistry()

from sim_racecenter_agent.mcp.tools.get_live_snapshot import build_get_live_snapshot_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_current_battle import build_get_current_battle_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_fastest_practice import build_get_fastest_practice_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.search_corpus import build_search_corpus_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.search_chat import build_search_chat_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_roster import build_get_roster_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_session_history import build_get_session_history_tool  # noqa: E402
from sim_racecenter_agent.adapters.nats_listener import run_telemetry_listener  # noqa: E402
import os  # noqa: E402


def _stdout_write(obj: Dict[str, Any]):  # atomic-ish line write
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


async def _stdin_lines():
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if line == "":  # EOF
            break
        yield line.rstrip("\n")


async def _register_tools(cache: StateCache):
    for tool_def in [
        build_get_live_snapshot_tool(cache),
        build_search_corpus_tool(),
        build_get_current_battle_tool(cache),
        build_search_chat_tool(),
        build_get_fastest_practice_tool(cache),
        build_get_roster_tool(cache),
        build_get_session_history_tool(cache),
    ]:
        # Guard against double registration (idempotent)
        name = tool_def["name"]
        if name in tool_registry.list_tools():  # skip if already there
            continue
        tool_registry.register(
            name=name,
            description=tool_def["description"],
            input_schema=tool_def["input_schema"],
            output_schema=tool_def["output_schema"],
            handler=tool_def["handler"],
        )


async def main():
    settings = get_settings()
    cache = StateCache(settings.snapshot_pos_history, settings.incident_ring_size)
    await _register_tools(cache)

    # Start telemetry listener unless disabled (disabled by default here)
    stop_event = asyncio.Event()
    # Default ON: explicitly set DISABLE_INGEST=1 to suppress telemetry listener
    disable_ingest = os.getenv("DISABLE_INGEST", "0") == "1"
    listener_task = None
    if disable_ingest:
        # print to stderr so stdout remains pure JSON-RPC responses for tests/clients
        print(
            "[mcp_stdio] telemetry ingestion disabled (DISABLE_INGEST=1 or default)",
            file=sys.stderr,
        )
    else:
        listener_task = asyncio.create_task(run_telemetry_listener(cache, settings, stop_event))

    async for raw in _stdin_lines():
        if not raw.strip():
            continue
        try:
            req = json.loads(raw)
        except Exception as e:  # malformed JSON
            _stdout_write(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {e}"}}
            )
            continue
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        try:
            if method == "initialize":
                _stdout_write(
                    {
                        "jsonrpc": "2.0",
                        "id": rid,
                        "result": {
                            "serverInfo": {"name": "sim-racecenter", "version": "0.1.0"},
                            "capabilities": {"tools": {}},
                        },
                    }
                )
            elif method == "tools/list" or method == "list_tools":  # backward compat
                tools_meta = []
                for tool in tool_registry.list_tools():
                    # tool already excludes handler
                    tools_meta.append(
                        {
                            "name": tool["name"],
                            "description": tool["description"],
                            "inputSchema": tool["input_schema"],
                        }
                    )
                # If legacy method list_tools, return simple list for tests
                if method == "list_tools":
                    _stdout_write({"jsonrpc": "2.0", "id": rid, "result": {"tools": tools_meta}})
                else:
                    _stdout_write({"jsonrpc": "2.0", "id": rid, "result": {"tools": tools_meta}})
            elif method == "tools/call" or method == "call_tool":  # backward compat
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if not isinstance(name, str):
                    raise ValueError("Tool name missing or not a string")
                result = tool_registry.call(name, arguments)
                # Legacy call_tool expects raw tool result at top-level result
                if method == "call_tool":
                    _stdout_write({"jsonrpc": "2.0", "id": rid, "result": result})
                else:
                    _stdout_write(
                        {
                            "jsonrpc": "2.0",
                            "id": rid,
                            "result": {"content": [{"type": "json", "value": result}]},
                        }
                    )
            elif method == "ping":  # convenience
                _stdout_write({"jsonrpc": "2.0", "id": rid, "result": {"pong": True}})
            else:
                _stdout_write(
                    {
                        "jsonrpc": "2.0",
                        "id": rid,
                        "error": {"code": -32601, "message": "Method not found"},
                    }
                )
        except Exception as e:  # tool or logic failure
            _stdout_write(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {
                        "code": -32000,
                        "message": str(e),
                        "data": traceback.format_exc(limit=4),
                    },
                }
            )

    # EOF received -> stop listener if running
    stop_event.set()
    if listener_task:
        try:
            await asyncio.wait_for(listener_task, timeout=5)
        except asyncio.TimeoutError:  # pragma: no cover
            pass


if __name__ == "__main__":  # pragma: no cover - integration entrypoint
    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # graceful shutdown
        pass

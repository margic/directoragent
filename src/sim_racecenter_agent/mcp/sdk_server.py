from __future__ import annotations

# ruff: noqa: E402  (intentional sys.path manipulation before imports for flexible invocation)

"""FastMCP-based server exposing existing tools using the official MCP SDK.

Replaces the ad-hoc JSON-RPC implementations in `server.py` and `scripts/mcp_stdio.py`.
Maintains same tool names & semantics for compatibility.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
import sys
import pathlib

# Ensure package root (../..) is on sys.path when invoked via file path (no package context)
_PKG_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:  # runtime import guard (dependency added in pyproject)
    from mcp.server.fastmcp import FastMCP, Context
    from mcp.server.session import ServerSession
except Exception:  # pragma: no cover - allows module import even if mcp not installed yet
    FastMCP = Context = ServerSession = object  # type: ignore

import json
from sim_racecenter_agent.core.state_cache import StateCache
from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.adapters.nats_listener import run_telemetry_listener

# Placeholder; real instance created in _init_server()
mcp: FastMCP | None = None  # type: ignore[assignment]


# Lifespan context to manage StateCache + telemetry listener
class AppContext:
    def __init__(self, cache: StateCache, stop_event: asyncio.Event, listener_task: asyncio.Task):
        self.cache = cache
        self.stop_event = stop_event
        self.listener_task = listener_task


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:  # type: ignore[override]
    settings = get_settings()
    cache = StateCache(settings.snapshot_pos_history, settings.incident_ring_size)
    stop_event = asyncio.Event()
    listener_task = asyncio.create_task(run_telemetry_listener(cache, settings, stop_event))
    try:
        yield AppContext(cache, stop_event, listener_task)
    finally:  # graceful shutdown
        stop_event.set()
        try:
            await asyncio.wait_for(listener_task, timeout=10)
        except asyncio.TimeoutError:  # pragma: no cover
            pass


# Lifespan will be passed into FastMCP constructor below.

# Tool adapters (reusing existing logic functions)
from sim_racecenter_agent.mcp.tools.get_live_snapshot import build_get_live_snapshot_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_current_battle import build_get_current_battle_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_fastest_practice import build_get_fastest_practice_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.search_corpus import build_search_corpus_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.search_chat import build_search_chat_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_roster import build_get_roster_tool  # noqa: E402
from sim_racecenter_agent.mcp.tools.get_session_history import build_get_session_history_tool  # noqa: E402

# Each existing build_* returns dict with handler(cache) signature -> wrap into FastMCP tool
# We'll manually register because decorators would require rewriting handlers with signature.

_existing_builders = [
    build_get_live_snapshot_tool,
    build_get_current_battle_tool,
    build_get_fastest_practice_tool,
    build_search_corpus_tool,
    build_search_chat_tool,
    build_get_roster_tool,
    build_get_session_history_tool,
]


def _register_legacy_tools():
    """Register tools by wrapping existing builder pattern.

    We defer building handlers until call-time so we can pass the live cache
    from the lifespan context instead of constructing a placeholder cache at import time.
    """

    for build in _existing_builders:
        # Introspect whether builder expects a cache parameter
        needs_cache = build.__code__.co_argcount == 1
        # Build once with a dummy cache only to extract static metadata (name/description/schema)
        dummy_cache = StateCache(1, 1)
        spec = build(dummy_cache) if needs_cache else build()
        name = spec["name"]
        description = spec.get("description", name)

        def _make(spec: dict, needs_cache: bool):  # capture loop vars
            input_props_local = spec.get("input_schema", {}).get("properties", {})

            async def _tool(ctx: Context[ServerSession, AppContext], **kwargs: Any) -> dict:  # type: ignore[type-var]
                cache = ctx.request_context.lifespan_context.cache
                # Rebuild spec each call if builder uses cache (to bind fresh cache ref)
                active_spec = build(cache) if needs_cache else spec
                handler = active_spec["handler"]
                args = {k: v for k, v in kwargs.items() if k in input_props_local}
                result = handler(args)
                if isinstance(result, dict) and "generated_at" not in result:
                    result.setdefault(
                        "generated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    )
                return result

            _tool.__name__ = spec["name"]  # type: ignore[attr-defined]
            return _tool

        tool_fn = _make(spec, needs_cache)
        mcp.tool(name=name, description=description)(tool_fn)  # type: ignore[misc]


def _init_server():
    global mcp
    instance = FastMCP(
        name="Sim RaceCenter",
        instructions="Race telemetry & director tools.",
        lifespan=lifespan,  # type: ignore[arg-type]
    )
    mcp = instance
    _register_legacy_tools()
    return instance


mcp = _init_server()

# Entry points


def run_stdio():  # Replacement for scripts/mcp_stdio.py
    if hasattr(mcp, "run"):
        # If incoming first line looks like legacy JSON-RPC (has method list_tools or tools/list without proper initialize),
        # we shim minimal handling by spawning a lightweight JSON-RPC loop using existing tool handlers.
        # Heuristic: peek first stdin line without consuming for normal FastMCP if it is a valid FastMCP initialize (contains 'initialize').
        try:
            data = sys.stdin.read()
            if data.strip():
                lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
                # Legacy if any line has list_tools / call_tool
                if any(json.loads(ln).get("method") in {"list_tools", "call_tool"} for ln in lines):
                    tools: dict[str, Any] = {}
                    dummy_cache = StateCache(1, 1)
                    for build in _existing_builders:
                        spec = build(dummy_cache) if build.__code__.co_argcount == 1 else build()
                        tools[spec["name"]] = spec
                    for line in lines:
                        try:
                            req = json.loads(line)
                        except Exception as e:
                            sys.stdout.write(
                                json.dumps(
                                    {
                                        "jsonrpc": "2.0",
                                        "error": {"code": -32700, "message": f"Parse error: {e}"},
                                    }
                                )
                                + "\n"
                            )
                            continue
                        rid = req.get("id")
                        m = req.get("method")
                        if m == "list_tools":
                            meta = [
                                {
                                    "name": n,
                                    "description": t.get("description"),
                                    "inputSchema": t.get("input_schema"),
                                }
                                for n, t in tools.items()
                            ]
                            sys.stdout.write(
                                json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"tools": meta}})
                                + "\n"
                            )
                        elif m == "call_tool":
                            params = req.get("params") or {}
                            name = params.get("name")
                            args = params.get("arguments") or {}
                            if name not in tools:
                                sys.stdout.write(
                                    json.dumps(
                                        {
                                            "jsonrpc": "2.0",
                                            "id": rid,
                                            "error": {"code": -32601, "message": "Unknown tool"},
                                        }
                                    )
                                    + "\n"
                                )
                            else:
                                try:
                                    res = tools[name]["handler"](args)
                                    sys.stdout.write(
                                        json.dumps({"jsonrpc": "2.0", "id": rid, "result": res})
                                        + "\n"
                                    )
                                except Exception as e:
                                    sys.stdout.write(
                                        json.dumps(
                                            {
                                                "jsonrpc": "2.0",
                                                "id": rid,
                                                "error": {"code": -32000, "message": str(e)},
                                            }
                                        )
                                        + "\n"
                                    )
                        else:
                            sys.stdout.write(
                                json.dumps(
                                    {
                                        "jsonrpc": "2.0",
                                        "id": rid,
                                        "error": {"code": -32601, "message": "Method not found"},
                                    }
                                )
                                + "\n"
                            )
                    sys.stdout.flush()
                    return
            # No legacy trigger -> fallback to FastMCP run (no input consumed)
        except Exception:  # pragma: no cover
            pass
        mcp.run(transport="stdio")  # type: ignore[attr-defined]
    else:  # pragma: no cover
        raise RuntimeError("FastMCP not available (dependency not installed)")


def run_streamable_http():  # Optional HTTP transport
    if hasattr(mcp, "run"):
        mcp.run(transport="streamable-http")  # type: ignore[attr-defined]
    else:  # pragma: no cover
        raise RuntimeError("FastMCP not available (dependency not installed)")


# Expose server object & run() for MCP CLI import style (e.g. 'mcp run sdk_server.py:mcp')
server = mcp  # MCP CLI looks for .run()


def run():  # for module-style invocation expecting a call to run()
    mcp.run(transport="stdio")  # type: ignore[attr-defined]


if __name__ == "__main__":  # default to stdio
    run_stdio()

from __future__ import annotations
from sim_racecenter_agent.mcp.tools.get_session_history import build_get_session_history_tool
from sim_racecenter_agent.mcp.tools.get_roster import build_get_roster_tool
from sim_racecenter_agent.mcp.tools.search_chat import build_search_chat_tool
from sim_racecenter_agent.mcp.tools.search_corpus import build_search_corpus_tool
from sim_racecenter_agent.mcp.tools.get_fastest_practice import build_get_fastest_practice_tool
from sim_racecenter_agent.mcp.tools.get_current_battle import build_get_current_battle_tool
from sim_racecenter_agent.mcp.tools.get_live_snapshot import build_get_live_snapshot_tool
from sim_racecenter_agent.mcp.tools._meta import add_meta
from sim_racecenter_agent.adapters.nats_listener import run_telemetry_listener
from sim_racecenter_agent.config.settings import get_settings
from sim_racecenter_agent.core.state_cache import StateCache

# ruff: noqa: E402  (intentional sys.path manipulation before imports for flexible invocation)
"""FastMCP-based server exposing existing tools using the official MCP SDK.

Replaces the ad-hoc JSON-RPC implementations in `server.py` and `scripts/mcp_stdio.py`.
Maintains same tool names & semantics for compatibility.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
import sys
import pathlib
import json

_PKG_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    from mcp.server.fastmcp import FastMCP, Context
    from mcp.server.session import ServerSession
except Exception:  # pragma: no cover
    FastMCP = Context = ServerSession = object  # type: ignore


mcp: FastMCP | None = None  # type: ignore[assignment]


class AppContext:
    def __init__(self, cache: StateCache, stop_event: asyncio.Event, listener_task: asyncio.Task):
        self.cache = cache
        self.stop_event = stop_event
        self.listener_task = listener_task
        import time as _t

        self.started_at = _t.time()


_LAST_APP_CONTEXT: AppContext | None = None


@asynccontextmanager
# type: ignore[override]
async def lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    settings = get_settings()
    cache = StateCache(settings.snapshot_pos_history, settings.incident_ring_size)
    stop_event = asyncio.Event()
    listener_task = asyncio.create_task(run_telemetry_listener(cache, settings, stop_event))
    ctx = AppContext(cache, stop_event, listener_task)
    global _LAST_APP_CONTEXT
    _LAST_APP_CONTEXT = ctx
    try:
        yield ctx
    finally:  # graceful shutdown
        stop_event.set()
        try:
            await asyncio.wait_for(listener_task, timeout=10)
        except asyncio.TimeoutError:  # pragma: no cover
            pass


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
    dummy_cache = StateCache(1, 1)
    for build in _existing_builders:
        needs_cache = build.__code__.co_argcount == 1
        spec = build(dummy_cache) if needs_cache else build()
        name = spec["name"]
        description = spec.get("description", name)
        input_props_local = spec.get("input_schema", {}).get("properties", {})
        # Simpler closure-based wrapper; no context parameter so FastMCP won't require one.

        def _make(active_spec: dict, needs_cache_flag: bool, input_props: dict[str, Any]):
            # Build explicit parameter list so pydantic model doesn't create a 'kwargs' required field.
            params = ", ".join(f"{k}: Any | None = None" for k in input_props.keys())
            header = f"async def _wrapper({params}):" if params else "async def _wrapper():"
            body = [
                "    from sim_racecenter_agent.mcp.sdk_server import _LAST_APP_CONTEXT, StateCache",
                "    cache = _LAST_APP_CONTEXT.cache if _LAST_APP_CONTEXT else StateCache(1,1)",
                "    spec_local = build(cache) if needs_cache_flag else active_spec",
                "    handler = spec_local['handler']",
                "    args: dict[str, Any] = {}",
            ]
            for k in input_props.keys():
                body.append(f"    if {k} is not None: args['{k}'] = {k}")
            body.append("    return handler(args)")
            src = "\n".join([header] + body)
            local_ns: dict[str, Any] = {
                "Any": Any,
                "build": build,
                "needs_cache_flag": needs_cache_flag,
                "active_spec": active_spec,
            }
            exec(src, local_ns, local_ns)
            fn = local_ns["_wrapper"]
            fn.__name__ = active_spec["name"]  # type: ignore[attr-defined]
            return fn

        tool_fn = _make(spec, needs_cache, input_props_local)
        if mcp is not None:
            mcp.tool(name=name, description=description)(tool_fn)  # type: ignore[misc]


def _init_server():
    global mcp
    instance = FastMCP(lifespan=lifespan)  # type: ignore[arg-type]
    mcp = instance
    _register_legacy_tools()
    return instance


mcp = _init_server()

# ----------------- Additional diagnostic & persistence tools (not in legacy builders) -----------------


# type: ignore[misc]
@mcp.tool(
    name="get_operational_status",
    description="Operational status: ingest running, cache stats, uptime",
)
async def get_operational_status() -> dict:
    import time as _t

    ctx = _LAST_APP_CONTEXT
    telemetry_running = bool(ctx and ctx.listener_task and not ctx.listener_task.done())
    # always enabled unless disabled via env (simplified)
    telemetry_enabled = not (get_settings() and (False))
    uptime_s = None
    if ctx:
        uptime_s = max(0.0, _t.time() - getattr(ctx, "started_at", _t.time()))
        cache = ctx.cache
    else:
        cache = StateCache(1, 1)
    result = {
        "telemetry_ingest": {"enabled": telemetry_enabled, "running": telemetry_running},
        "uptime_s": round(uptime_s, 3) if uptime_s is not None else None,
        "cache": {
            "roster_size": len(cache.roster()),
            "lap_timing_records": len(cache.lap_timing()),
            "standings_records": len(cache.standings()),
            "has_session_state": bool(cache.session_state()),
        },
    }
    return add_meta(result)


# type: ignore[misc]
# type: ignore[misc]
@mcp.tool(
    name="get_recent_chat_messages", description="Recent ingested chat messages (newest first)"
)
async def get_recent_chat_messages(limit: int = 25) -> dict:
    ctx = _LAST_APP_CONTEXT
    if not ctx:
        result = {"messages": [], "limit": 0, "error": "no_context"}
        return add_meta(result)
    lim = max(1, min(int(limit), 100))
    msgs = ctx.cache.recent_chat(lim)
    result = {"messages": list(reversed(msgs)), "limit": lim, "count": len(msgs)}
    return add_meta(result)


# type: ignore[misc]
@mcp.tool(
    name="get_session_persistence_status",
    description="Snapshot table row counts & latest timestamps",
)
async def get_session_persistence_status() -> dict:
    import sqlite3
    import os
    import time as _t

    settings = get_settings()
    path = settings.sqlite_path
    out: dict[str, object] = {"sqlite_path": path}
    tables = [
        "session_snapshots",
        "session_state_snapshots",
        "standings_snapshots",
        "track_conditions_snapshots",
    ]
    if not os.path.exists(path):
        out["error"] = "sqlite_missing"
        return add_meta(out)
    try:
        conn = sqlite3.connect(path)
        try:
            for t in tables:
                try:
                    # type: ignore[misc]
                    c, last = conn.execute(f"SELECT COUNT(*), MAX(ts) FROM {t}").fetchone()
                    out[t] = {"count": int(c or 0), "last_ts": last}
                except Exception:
                    out[t] = {"count": 0, "last_ts": None, "error": "query_failed"}
        finally:
            conn.close()
    except Exception as e:  # pragma: no cover
        out["error"] = f"sqlite_open_failed:{e}"
    out["queried_ts"] = f"{_t.time():.6f}"
    return add_meta(out)


def run_stdio():
    if hasattr(mcp, "run"):
        try:
            data = sys.stdin.read()
            if data.strip():
                lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
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


server = mcp  # MCP CLI expects .run()


def run():
    mcp.run(transport="stdio")  # type: ignore[attr-defined]


if __name__ == "__main__":
    run_stdio()

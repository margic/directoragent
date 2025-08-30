from __future__ import annotations
from fastapi import FastAPI, HTTPException
import logging
import inspect
from pydantic import BaseModel
from sim_racecenter_agent.mcp.sdk_server import mcp  # type: ignore

"""Minimal HTTP API exposing list_tools and call_tool endpoints.

Endpoints:
    GET /mcp/list_tools -> {"tools": [{name, description, input_schema}]}
    POST /mcp/call_tool {"name": str, "arguments": {}} -> {"result": {...}}
"""

_LOG = logging.getLogger("mcp_http_api")

app = FastAPI(title="Sim RaceCenter MCP API", version="0.1")


class CallToolRequest(BaseModel):
    name: str
    arguments: dict = {}


@app.get("/mcp/list_tools")
async def list_tools():  # type: ignore[override]
    if mcp is None:  # type: ignore
        raise HTTPException(status_code=500, detail="MCP server not initialized")
    try:
        raw = mcp.list_tools()  # type: ignore[attr-defined]
        # Some FastMCP APIs may return awaitables or nested awaitables
        while inspect.isawaitable(raw):  # type: ignore
            raw = await raw  # type: ignore
        # Support possible object with .tools attribute
        if hasattr(raw, "tools") and not isinstance(raw, list):  # type: ignore
            candidate = getattr(raw, "tools")  # type: ignore
        else:
            candidate = raw
        if not isinstance(candidate, (list, tuple)):
            raise RuntimeError("Unexpected list_tools return type")
        tools = []
        for t in candidate:  # type: ignore
            tools.append(
                {
                    "name": getattr(t, "name", None),
                    "description": getattr(t, "description", getattr(t, "name", "")),
                    "input_schema": getattr(t, "input_schema", {}),
                }
            )
        return {"tools": tools}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/call_tool")
async def call_tool(req: CallToolRequest):  # type: ignore[override]
    try:
        if mcp is None:  # type: ignore
            raise RuntimeError("MCP server not initialized")
        # Invoke the tool via FastMCP. Some implementations may return nested awaitables.
        # FastMCP expects positional (name, arguments: dict). Use fallback to legacy kwargs style if needed.
        try:
            # type: ignore[attr-defined]
            raw = mcp.call_tool(req.name, arguments=req.arguments or {})
        except TypeError:
            # fallback for older signature
            raw = mcp.call_tool(req.name, **(req.arguments or {}))
        while inspect.isawaitable(raw):  # type: ignore
            raw = await raw  # type: ignore
        return {"result": raw}
    except Exception as e:
        _LOG.debug("call_tool error name=%s args=%s err=%s", req.name, req.arguments, e)
        raise HTTPException(status_code=400, detail=str(e))

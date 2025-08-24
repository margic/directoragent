from __future__ import annotations

import asyncio

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from ..config.settings import get_settings
from ..core.state_cache import StateCache
from .registry import tool_registry
from .tools.get_current_battle import build_get_current_battle_tool
from .tools.get_live_snapshot import build_get_live_snapshot_tool
from .tools.search_chat import build_search_chat_tool
from .tools.search_corpus import build_search_corpus_tool


def create_app(cache: StateCache) -> FastAPI:
    app = FastAPI(title="Sim RaceCenter MCP Server", version="0.1.0")
    router = APIRouter()

    @router.get("/mcp/list_tools")
    async def list_tools():
        return {"tools": tool_registry.list_tools()}

    @router.post("/mcp/call_tool")
    async def call_tool(payload: dict):
        name = payload.get("name")
        args = payload.get("arguments", {})
        if not isinstance(name, str):
            return JSONResponse(status_code=400, content={"error": "Missing tool name"})
        try:
            result = tool_registry.call(name, args)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": str(e)})
        return {"result": result}

    app.include_router(router)
    return app


async def bootstrap() -> None:
    settings = get_settings()
    cache = StateCache(settings.snapshot_pos_history, settings.incident_ring_size)

    # Register tools (stub)
    for tool_def in [
        build_get_live_snapshot_tool(cache),
        build_search_corpus_tool(),
        build_get_current_battle_tool(cache),
        build_search_chat_tool(),
    ]:
        tool_registry.register(
            name=tool_def["name"],
            description=tool_def["description"],
            input_schema=tool_def["input_schema"],
            output_schema=tool_def["output_schema"],
            handler=tool_def["handler"],
        )

    app = create_app(cache)
    config = uvicorn.Config(app, host="0.0.0.0", port=settings.mcp_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(bootstrap())

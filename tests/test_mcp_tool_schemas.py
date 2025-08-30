import pytest

from sim_racecenter_agent.mcp.sdk_server import mcp


@pytest.mark.asyncio
async def test_tool_input_schemas_structure():
    """Each tool should expose a JSON schema with properties and type."""
    assert mcp is not None
    tools = await mcp.list_tools()
    assert tools, "No tools registered"
    for t in tools:
        schema = t.inputSchema  # FastMCP Tool attribute
        assert isinstance(schema, dict), f"Schema not dict for {t.name}"
        assert schema.get("type") == "object", f"Schema type not object for {t.name}"
        assert "properties" in schema, f"Missing properties for {t.name}"
        # Properties can be empty for some tools (like get_live_snapshot)
        props = schema["properties"]
        assert isinstance(props, dict), f"Properties not dict for {t.name}"


@pytest.mark.asyncio
async def test_tool_required_constraints():
    """Search tools should have query parameters available (though not necessarily required)."""
    tools = await mcp.list_tools()
    by_name = {t.name: t for t in tools}
    search_chat = by_name.get("search_chat")
    search_corpus = by_name.get("search_corpus")
    for search_tool in (search_chat, search_corpus):
        assert search_tool is not None, f"Search tool {search_tool} not found"
        props = search_tool.inputSchema.get("properties", {})
        assert "query" in props, f"query property missing for {search_tool.name}"
    # Non-search tools should either have no required list or not require optional params
    for name, tool in by_name.items():
        if name in {"search_chat", "search_corpus"}:
            continue
        req = set(tool.inputSchema.get("required", []))
        # Only context may appear (some tools auto-inject context) but should not block invocation
        assert (
            not req or req == {"context"} or req == set()
        ), f"Unexpected required params for {name}: {req}"


@pytest.mark.asyncio
async def test_tool_metadata_response_fields():
    """All tools should include schema_version + generated_at in responses via add_meta."""
    tools = await mcp.list_tools()
    for t in tools:
        # Minimal invocation args (exclude context; sdk supplies runtime Context)
        call_args = {}
        if t.name == "get_current_battle":
            call_args = {"top_n_pairs": 1}
        elif t.name == "get_fastest_practice":
            call_args = {"top_n": 1}
        elif t.name == "get_session_history":
            call_args = {"limit": 1}
        elif t.name in {"search_chat", "search_corpus"}:
            call_args = {"query": "test", "limit": 1}
        required = set(t.inputSchema.get("required", []))
        if "context" in required:
            call_args["context"] = {}
        try:
            raw = await mcp.call_tool(t.name, call_args)
        except Exception as e:  # ToolError wrapper
            import pytest

            if "Context is not available outside of a request" in str(e):
                pytest.skip(f"Skipping {t.name} requires live request context")
            raise
        if isinstance(raw, list) and raw and getattr(raw[0], "type", None) == "text":
            import json as _json

            result = _json.loads(raw[0].text)
        else:
            result = raw
        assert isinstance(result, dict), f"Result not dict for {t.name}: {type(result)}"
        assert "schema_version" in result, f"schema_version missing for {t.name}"
        assert "generated_at" in result, f"generated_at missing for {t.name}"
        # Basic type checks
        assert isinstance(result["schema_version"], int)
        assert isinstance(result["generated_at"], str)

# Sim RaceCenter Agent

Agent + MCP layer for Sim RaceCenter: exposes race domain data (via NATS JetStream + SQLite) to LLM tooling and powers a Director chat responder.

## Quick Start (Dev Container)

1. Clone repo and open in VS Code
2. Reopen in container when prompted
3. Initialize DB (placeholder)

## MCP Server (Official SDK)

The legacy FastAPI + custom stdio implementations have been removed. The project now uses the official Python MCP SDK (FastMCP) with a single stdio transport entrypoint.

Run (stdio transport):
```
python -m sim_racecenter_agent.mcp.sdk_server
```

Optional streamable HTTP (adds MCP spec HTTP transport):
```
python -m sim_racecenter_agent.mcp.sdk_server --transport http   # (if you wrap a small CLI)
```

### Copilot Chat Integration
The devcontainer already registers the server under the key `racecenter`. Open Copilot Chat and ask: *Who is leading? racecenter*.

### MCP CLI Usage (Updated)
The `--server` flag no longer exists. Use `run` (just run server) or `dev` (run with Inspector):

Run with Inspector (interactive tool browser):
```
mcp dev src/sim_racecenter_agent/mcp/sdk_server.py
```
Run plain server (stdio transport):
```
mcp run src/sim_racecenter_agent/mcp/sdk_server.py
```
Legacy JSON-RPC style manual tool listing (for quick shell test):
```
echo '{"jsonrpc":"2.0","id":1,"method":"list_tools"}' | python -m sim_racecenter_agent.mcp.sdk_server
```
Call a tool manually:
```
echo '{"jsonrpc":"2.0","id":2,"method":"call_tool","params":{"name":"get_current_battle","arguments":{"top_n_pairs":1}}}' | python -m sim_racecenter_agent.mcp.sdk_server
```

### Development Notes
* Tools are registered dynamically in `sdk_server.py` by wrapping existing `build_*` factory functions.
* Telemetry ingestion runs inside the FastMCP lifespan context.
* Remove any remaining imports of `mcp.server` or `tool_registry` if you add new code (they were deleted).

## Director Agent – Single LLM Mode
The Director chat responder now operates ONLY in a single high‑quality LLM planning + answer mode (no heuristic / intent fallback). Every incoming chat message:
1. Planner call (Gemini) decides which MCP tools to invoke (may return empty -> message ignored).
2. Agent executes permitted tools and collects JSON results.
3. Answer call (Gemini) produces a concise (<=200 chars) response using ONLY those tool results.
4. Empty/invalid plan or missing API key => silent ignore (noise reduction, no low‑quality guesses).

### Rationale
Designed for a live racing YouTube stream with moderate chat throughput: prioritizes contextual accuracy and clarity over minimal latency or token cost.

### Environment Variables
Set before running the server (examples). Defaults in code are gemini-2.5-flash for both planner & answer; override if desired:
```
export GEMINI_API_KEY=your_key_here
export LLM_PLANNER_MODEL=gemini-2.5-flash      # (default in code)
export LLM_ANSWER_MODEL=gemini-2.5-flash       # (default in code)
```
If `GEMINI_API_KEY` is unset, planning returns None and messages are ignored.

### Upgrading / Adding Tools
Add a new tool implementation and ensure it is registered in `sdk_server.py`. The planner automatically sees it in the catalog (no intent routing edits required).

### Deprecated
`core/llm_intent.py` now raises on use; legacy intent / heuristic branches were removed from `director/agent.py`.

### Future Enhancements (Planned)
* Structured logging of (message, plan, execution timings, answer)
* Rate limiting + duplicate suppression
* Optional moderation / safety filter pass


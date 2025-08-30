# Sim RaceCenter Agent

Agent + MCP layer for Sim RaceCenter: exposes race domain data (via NATS JetStream + SQLite) to LLM tooling and powers a Director chat responder.

## Key Documentation
* [Specification](docs/spec.md)
* [MVP v1 Definition](docs/mvp_v1_definition.md)
* [Use Cases](docs/use_cases.md)
* [FastMCP Design Patterns](docs/fastmcp_design_patterns.md)
* [Tool API Schemas](docs/api_mcp_tools.md)

## Quick Start (Dev Container)

1. Clone repo and open in VS Code
2. Reopen in container when prompted
3. Initialize DB (placeholder)

## Test Suite Overview


## MCP Server (Official SDK – stdio only)

The agent uses the official Python MCP SDK (FastMCP) over a single stdio transport. All legacy HTTP / REST / JSON-RPC shim code and the prior dict-based builder pattern have been removed. Tools are declared as async functions decorated with `@mcp.tool` inside `sdk_server.py` (kept co-located for now for minimal complexity).

Run standalone server for a quick manual smoke test:
```
python -m sim_racecenter_agent.mcp.sdk_server
```


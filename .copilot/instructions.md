# Copilot Implementation Guidance

This repository follows a spec-first approach (see docs/spec.md). When generating code:

1. Favor pure functions in tools (no side effects).
2. All MCP tool outputs must contain `schema_version`.
3. Keep tool implementations in `src/sim_racecenter_agent/mcp/tools/`.
4. Do not perform JetStream pulls inside tool handlers—use cached state.
5. Use pydantic models for:
   - Settings
   - Tool inputs/outputs
   - Internal domain models (incidents, snapshot)
6. Add logging for each tool call: logger name `tool.<name>`.
7. Expand tests incrementally:
   - Start with state_cache behavior
   - Then tool response shapes
8. Provide type hints everywhere; pass mypy (strict) if feasible.
9. Stage future work behind TODO markers referencing spec sections.
10. Register new tools by adding a build_* function and appending it to `_existing_builders` in `mcp/sdk_server.py` (FastMCP server).
11. Ensure every tool response includes `generated_at` when synthesizing data and uses consistent numeric units.
12. If adding new NATS subjects, update: `docs/nats-messages.md`, `docs/iracing_extended_metrics_spec.md`, schemas in `src/sim_racecenter_agent/schemas/`, and link them from the main spec Related Documents section.
13. Prefer updating or adding JSON Schemas before writing ingestion logic; validate via `schemas.validation.is_valid` in handlers.

TODO (FastMCP alignment):
- [ ] Add `schema_version` to get_fastest_practice, get_roster, get_session_history.
- [ ] Add `generated_at` to get_session_history output.
- [ ] Remove deprecated `mcp/server.py` once no external consumers.

If unsure about structure, read docs/spec.md (source of truth).
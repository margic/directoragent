# FastMCP Design & Usage Patterns

Status: DRAFT – internal guidance on how we apply FastMCP (see official docs:
- Server: https://gofastmcp.com/servers/server
- Gemini Integration: https://gofastmcp.com/integrations/gemini

This file captures project‑specific conventions so contributors need not reverse‑engineer the running code.

## 1. Core Objectives
1. Keep all MCP tool registrations centralized for discoverability & test hooks.
2. Enforce strict input validation (JSON Schema or Pydantic) before handler logic.
3. Provide deterministic, minimal output envelopes (schema_version, generated_at, payload fields, optional error object).
4. Separate planning (LLM) from execution (tool handlers) – no direct tool invocation from LLM output without validation.
5. Preserve backward compatibility with versioned schemas; additive changes default; breaking changes bump `schema_version`.

## 2. Server Lifecycle Pattern
| Phase | Action | Notes |
|-------|--------|-------|
| Bootstrap | Load Settings, init StateCache, DB connections (lazy where possible) | Fail fast on unrecoverable config errors |
| Tool Registration | Call builder functions (e.g., `build_get_current_battle_tool(cache)`) | Each returns dict spec consumed by FastMCP server |
| Start | Launch FastMCP stdio server in same process thread as director orchestration | Simplicity > multi-process in early phases |
| Shutdown | Graceful: flush any pending logs, close DB/ NATS connections | Handled by signal handlers (TODO) |

## 3. Tool Registration Pattern
```python
# sdk_server.py (excerpt)
TOOLS = [
    build_get_live_snapshot_tool(cache),
    build_get_current_battle_tool(cache),
    ...
]
server = FastMCPServer(tools=TOOLS, middlewares=[logging_mw, timing_mw])
```
Guidelines:
- One builder per tool returning `{ name, description, input_schema, output_schema, handler }`.
- No network calls inside handlers (read from cache / local DB only); external IO belongs upstream ingestion.
- Keep handler pure; side-effect only = metrics counters or debug logging.

## 4. Input Validation Pattern
- Prefer JSON Schema for lightweight validation (FastMCP native) and mirror complex logic via Pydantic if needed.
- Reject invalid payloads early; respond with `{"schema_version": X, "error": {"type": "validation_error", ...}}`.
- Enforce numeric bounds (distance thresholds, list limits) to prevent unbounded responses.

## 5. Planning & Execution Pattern
1. Planner LLM receives tool catalog summary (name + description + input schema snippet).
2. LLM returns tentative plan JSON list.
3. Validation step filters unknown names, clamps arguments (e.g., max `top_n_pairs`).
4. Execute sequentially (future: DAG / parallel when dependency metadata added).
5. Aggregate outputs into answer prompt context.

## 6. Error Envelope Pattern
```json
{
  "schema_version": 1,
  "error": {"type": "tool_failed", "message": "<short>"}
}
```
Rules:
- Keep messages terse; detailed trace only in logs.
- Do not throw raw exceptions to caller; convert to error envelope.
- Tools never raise unhandled exceptions (tests enforce).

## 7. Concurrency & Performance
- Handlers should be O(n) over currently cached subset (e.g., number of drivers) and typically <50ms.
- Avoid per-call DB opens if possible; use lazy open + caching or connection pooling (future).
- Planner + Answer calls run async with timeouts (configurable). On timeout: silent drop (fail-silent).

## 8. Schema Versioning Strategy
| Change Type | Action |
|-------------|--------|
| Add optional field | Same schema_version |
| Add required field | Bump schema_version and reflect in docs/schemas/*.json |
| Rename / Remove field | Bump schema_version; maintain deprecation note for at least one increment |
| Change type/semantics | Bump schema_version; add migration note |

## 9. Logging & Metrics Middleware (Planned)
- Middleware wraps handler: start time, end time, exception capture.
- Emit structured log: `{tool, duration_ms, ok, rows_returned, error_type?}`.
- Counters updated for success/failure.

## 10. Security Boundaries
- LLM receives only sanitized tool outputs (no raw stack traces, no secrets).
- Planner restricted to known tool names (explicit allowlist).
- Input schemas ensure we never permit arbitrary file system paths or shell commands.

## 11. Testing Pattern
| Test Type | Focus | Example |
|-----------|-------|---------|
| Unit | Handler deterministic logic | battle pair ordering |
| Integration | Tool + Cache interactions | populate cache then call get_live_snapshot |
| Contract | JSON matches schema (schema_version) | compare with stored schema fixture |
| Planner | Plan validity (stub LLM) | synthetic message -> expected tool list |

## 12. Extension Hooks (Future)
- Middleware chain for rate limiting & auth (if operator UI).
- Streaming tool outputs (progress) – only when needed (not MVP).
- Parallel execution group annotation: tools declare `can_parallel: true`.

## 13. Gemini Integration Pattern
- Separate prompt templates for planner vs answer; keep under `director/reasoning.py` (or similar) so tests can snapshot.
- Provide tool catalog summary (name + short description + arg spec) compiled dynamically to avoid manual drift.
- Response JSON validated; on parse failure -> suppression (no fallback free-form answer).
- Temperature: low (planner) higher (answer) – config in Settings.

## 14. Deployment Notes
- Single process minimizes serialization overhead; revisit multi-process if CPU bound by LLM streaming / heavy embeddings.
- StdIO server suffices; add WebSocket transport only for external IDE/tool integration (non‑priority).

## 15. Open Questions
- Should we auto-generate tool catalog summary from JSON Schemas each startup? (Prototoype; may reduce drift risk.)
- Introduce plan caching for repeated identical questions during high volume?
- Add semantic similarity check to treat near-duplicate queries as same plan.

## 16. Quick Checklist (Contributor)
[ ] New tool builder file created under `mcp/tools/`  
[ ] JSON Schemas added/updated in `docs/schemas/`  
[ ] `sdk_server.py` registration updated  
[ ] Schema version bump if breaking  
[ ] Unit tests for handler edge cases  
[ ] Contract test verifying response keys  
[ ] Spec & api_mcp_tools.md updated if external behavior changes  

---
Update this document whenever adopting new FastMCP middleware patterns or changing schema versioning rules.

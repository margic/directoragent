# MCP Refactor & Alignment Plan

## 1. Objective
Align tool implementation with official FastMCP SDK guidance (decorator + typed args, stdio only), eliminating legacy builder pattern and JSON-RPC shim while preserving existing tool names and response shapes.

## 2. Scope
In-scope:
* Tool registration refactor (all existing tools)
* Removal of dynamic builder dicts & dummy cache instantiation
* Simplify `sdk_server.py` (no legacy stdin sniffing / shim)
* Consistent schema/version metadata injection
* Minimal test updates + new schema/tool catalog test

Out of scope (later):
* Adding new tools
* HTTP transport revival
* Operator UI / WS server
* Advanced auth / RBAC

## 3. Current State Summary
* Tools defined via `build_*` functions returning dicts (handler + metadata).
* `sdk_server.py` wraps these into FastMCP tools at runtime with a dummy cache.
* Agent uses stdio client correctly; no HTTP path.
* Legacy JSON-RPC compatibility shim still present in `run_stdio()`.

## 4. Target Architecture
* Each tool: async function with explicit typed params (primitive or Pydantic model) + `@mcp.tool` decorator.
* Single FastMCP instance created; importing `mcp.tools` auto-registers all tools.
* Lifespan context provides `cache`; tools access via `ctx.request_context.lifespan_context.cache`.
* Helper: `add_meta(result: dict)` adds `generated_at` & `schema_version` if missing.
* No JSON-RPC fallback code.

## 5. Phased Plan
| Phase | Description | Key Deliverables |
|-------|-------------|------------------|
| 1 | Introduce decorator pattern for 2 tools (`get_live_snapshot`, `get_current_battle`) in new modules; keep others legacy | New module(s), helper, dual registration working, tests green |
| 2 | Migrate remaining tools to decorators | All tools registered via decorators; legacy builders still present but unused |
| 3 | Remove legacy builder code & shim | Delete `_register_legacy_tools`, remove dummy cache + JSON-RPC fallback, prune unused imports |
| 4 | Hardening & tests | Add tool catalog test, meta helper test, docs update, finalize spec changes |

## 6. Detailed Tasks
T1: Create `mcp/tools/_meta.py` with `SCHEMA_VERSION`, `utc_now()`, `add_meta()`.
T2: Add `mcp/tools/snapshot.py` implementing decorator tool for `get_live_snapshot`.
T3: Add `mcp/tools/battle.py` implementing decorator tool for `get_current_battle`.
T4: Adjust `sdk_server.py` to import new modules (alongside legacy) and prefer decorated versions.
T5: Add test: `test_tool_catalog.py` verifying tool names & basic schema keys.
T6: Migrate remaining tools (practice, roster, session_history, search_corpus, search_chat).
T7: Remove legacy builder modules (or strip to thin wrappers calling new functions, then delete).
T8: Delete JSON-RPC fallback logic from `run_stdio()`.
T9: Update docs (`README.md`, `spec.md`) to reflect decorator & removal of legacy path.
T10: Add CHANGELOG or augment plan with completion notes.

## 7. Acceptance Criteria
AC1: All tools registered solely via decorators (no dummy cache in registration path).
AC2: `list_tools` returns identical tool names and compatible input schemas.
AC3: Tool outputs still honor prior field names; responses include `generated_at` + `schema_version`.
AC4: Test suite passes; new catalog test added.
AC5: No JSON-RPC fallback code remains in repository.
AC6: Documentation updated; no references to builder pattern or HTTP shim.

## 8. Risks & Mitigations
* Risk: Schema drift (argument names change) – Mitigate by keeping arg names identical; add catalog test early.
* Risk: Subtle output differences (missing meta fields) – Centralize in `add_meta` helper used by all tools.
* Risk: Large diff complicates review – Use phased PRs (Phase 1 & 2 incremental).
* Risk: Over-tight coupling to FastMCP internal API – Keep minimal dependency surface (Context only).

## 9. Rollback Strategy
* Phase 1 safe: legacy builders still intact.
* Prior to Phase 3, restore registration call to `_register_legacy_tools()` if needed.
* Tag repository before removing legacy code (e.g., `v0.1-legacy-builders`).

## 10. Testing Strategy
* Existing functional tests exercise snapshot & battle tool flows.
* New catalog test enumerates tools and asserts presence.
* Spot test: call each tool with empty args to ensure no exceptions.
* (Optional) Add quick pydantic argument validation test for one tool.

## 11. Documentation Updates
* README: Replace references to builder pattern with decorator approach.
* Spec: Update architecture & tool registration description.
* This plan file updated with completion checklist.

## 12. Completion Checklist
[x] T1  Meta helper
[x] T2  Decorator snapshot tool
[x] T3  Decorator battle tool
[x] T4  Dual registration working (superseded by full migration)
[x] T5  Catalog test
[x] T6  Migrate remaining tools
[x] T7  Remove legacy builders
[x] T8  Remove JSON-RPC fallback
[x] T9  Docs updated
[x] T10 Close plan / tag legacy (tag suggested: `v0.1-pre-fastmcp-decorators`)

## 13. Notes
Smallest viable first commit: T1–T4 + T5 (establishes pattern & safety net). Continue sequentially.

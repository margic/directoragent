# MCP Tool API Contracts

Status: PARTIAL (schemas v0.1). Each tool defines an input & output JSON Schema in `docs/schemas/` (draft 2020-12). All responses include:
- `schema_version` (int)
- `generated_at` (ISO8601 UTC) when synthesized

See `fastmcp_design_patterns.md` for overarching server/tool registration and error envelope conventions.

## get_live_snapshot
Schemas:
- Input: `schemas/get_live_snapshot.input.schema.json`
- Output: `schemas/get_live_snapshot.output.schema.json`
Notes: `standings_top`, `leaderboard`, `lap_timing_top` are partial lists (capped 15). Future additions (positions, gaps_s, flags) will increment `schema_version`.

## get_current_battle
Schemas:
- Input: `schemas/get_current_battle.input.schema.json`
- Output: `schemas/get_current_battle.output.schema.json`
Notes: `pairs` sorted ascending by `distance_m`; truncated to `top_n_requested`.

## get_fastest_practice
Schemas:
- Input: `schemas/get_fastest_practice.input.schema.json`
- Output: `schemas/get_fastest_practice.output.schema.json`
Notes: Uses lap timing if available else standings fallback; gaps computed vs fastest.

## get_roster
Schemas:
- Input: `schemas/get_roster.input.schema.json`
- Output: `schemas/get_roster.output.schema.json`
Notes: Full roster; `drivers` objects normalized (CarIdx, car, name).

## get_session_history
Schemas:
- Input: `schemas/get_session_history.input.schema.json`
- Output: `schemas/get_session_history.output.schema.json`
Notes: Most recent entries returned; ordering = chronological (latest last).

## search_chat
Schemas:
- Input: `schemas/search_chat.input.schema.json`
- Output: `schemas/search_chat.output.schema.json`
Notes: `results` sorted by bm25 ascending (lower is better). Optional username/day filters.

## search_corpus
Schemas:
- Input: `schemas/search_corpus.input.schema.json`
- Output: `schemas/search_corpus.output.schema.json`
Notes: Merges multi-scope FTS hits; includes per-scope `hit_counts` and `errors`.

## summarize_recent_events (DEFERRED)
Planned schemas: `summarize_recent_events.*` (not yet created) – awaits incident/event stream.

## propose_penalty (DEFERRED)
Planned schemas: `propose_penalty.*` – requires incident + penalty rules corpus.

## Error Envelope
Embedded inline per tool as needed. Pattern:
```
{ "schema_version": <int>, "error": {"type": "tool_failed", "message": "..."} }
```

## Version Negotiation (Future)
Client SHOULD inspect `schema_version`. Backward incompatible changes increment integer. Future: add optional `supported_versions` resource.

## Change Log
- v0.1: Initial schema set added (current file + /schemas directory).

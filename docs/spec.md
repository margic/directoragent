# Sim RaceCenter Agent – Technical Specification (v0.1)

## 1. Project Purpose
Provide an extensible “Agent Layer” that:
1. Bridges Sim RaceCenter domain data (NATS JetStream + SQLite) to LLM tooling via an MCP (Model Context Protocol) server.
2. Implements a Director Chat Agent that listens to YouTube chat and answers race-related questions using MCP tools.
3. Lays groundwork for operator moderation, FAQ learning, and potential highlight/analytics extensions.

This repository focuses on the agent & MCP layer (NOT raw telemetry ingestion—that lives in existing pyracing).

## 2. High-Level Architecture
```
+-------------------+           +--------------------+
|  pyracing Core    |  NATS JS  |  sim-racecenter-   |
|  (telemetry pub)  +---------->+  agent (this repo) |
+-------------------+           |  - MCP Server      |
                                |  - Director Agent  |
                                |  - Embedding Worker|
                                +----------+---------+
                                           |
                                           | (future) HTTP/WS (operator)
                                           v
                                   External Clients / Tooling
```

### Components
- adapters.nats_listener: Subscribes to JetStream streams (INCIDENTS, POSITIONS, EVENTS, SESSIONS, SUMMARIES).
- core.state_cache: In-memory rolling caches (leaderboard, incidents, events, position history).
- persistence.sqlite: Thin wrapper for SQLite (documents, embeddings, incidents_flat, driver_stats, summaries, answers_log, faq_pairs).
- embeddings.worker: Asynchronous embedding queue + in-memory vector index.
- mcp.server: JSON-RPC (MCP) with tool + resource registries.
- mcp.tools: Tool handlers (get_live_snapshot, summarize_recent_events, search_corpus, driver_card, describe_gap, predict_pit_window (stub), propose_penalty (stub)).
- director.chat_listener: Consumes chat events (from existing YouTube integration or future adapter).
- director.agent: Intent classification + tool invocation + answer assembly + (optional) moderation flow.
- config: Settings loading (env + .env) with pydantic models.
- logging/telemetry: Structured logs + basic metrics (timings per tool call).
- tasks: CLI utilities (bootstrap DB, run embedding backfill, debug tool call).

## 3. Data Sources & Persistence (Phase 1)
| Data Type              | Source          | Storage Mechanism               | Retention Strategy            |
|------------------------|-----------------|---------------------------------|------------------------------|
| Position snapshots (1Hz)| JetStream (RACE.POSITIONS) | In-memory ring buffer (900 frames) | 15 min window |
| Incidents              | JetStream (RACE.INCIDENTS) | Deque (300 recent) + SQLite incidents_flat | Full session persisted |
| Events (fastlap, battle)| JetStream (RACE.EVENTS)    | Deque (200 recent)              | 30–60 min |
| Session lifecycle       | JetStream (RACE.SESSION)   | Current session context          | Archive final summary |
| Summaries (partial)     | JetStream (RACE.SUMMARIES) | Keep last 10 + SQLite summaries  | Full session |
| Driver stats            | Computed post-session      | SQLite driver_stats              | Cumulative |
| Transcripts / docs      | External ingestion (future)| SQLite documents + embeddings    | All |
| Rules/FAQ               | Seed files / manual        | SQLite (faq_pairs) + local YAML  | All |
| Embeddings              | Derived                    | SQLite embeddings + in-memory matrix | Rebuild on change |

## 4. Tooling (Initial MCP Tools)
1. get_live_snapshot:
   - Input: optional fields list
   - Output: {timestamp, session, leaderboard[], flags, versions}
2. summarize_recent_events:
   - Input: window_seconds (default 180)
   - Output: {events[], narrative, window_seconds, generated_at}
3. search_corpus:
   - Input: query, top_k (default 5), scope (default all)
   - Output: {matches:[{doc_id, score, snippet, source_type}]}
4. driver_card:
   - Input: driver_id or car_number
   - Output: {driver_id, car_number, name, stats:{...}, style_tags[], updated_at}
5. describe_gap:
   - Input: leader_car, follower_car, window_seconds=120
   - Output: {leader_car, follower_car, current_gap_s, trend, deltas[], reasoning}
6. predict_pit_window (stub):
   - Input: car_number
   - Output: {car_number, projected_window_laps:[], confidence, assumptions, disclaimer}
7. propose_penalty (stub):
   - Input: incident_id
   - Output: {incident_id, classification, recommended_penalty, precedent_ids[], disclaimer}

## 5. MCP Resources (Phase 1)
- live/leaderboard.json
- live/incidents_recent.json
- live/events_recent.json
- live/session_meta.json
- cache/rolling_summary.json (latest partial summary)
- driver/{driver_id}.json (generated on-demand)
- rules/penalties.md (placeholder)
- faq/popular.json

## 6. Director Agent Flow
1. Receive chat message event -> classify intent (rule-based + simple keywords).
2. Map intent to required tool calls.
3. Call MCP tools (synchronously) – handle failures gracefully.
4. Assemble answer; enforce length (<200 chars).
5. (Optional) emit proposed answer for moderation; else post directly.
6. Log answer (SQLite answers_log).
7. Update FAQ learning counters (normalize repeated questions hashed by canonical form).

## 7. Intent Categories (Initial Heuristics)
| Category | Indicators | Tools |
|----------|-----------|-------|
| LEADER / GAP | “who’s leading”, “gap”, “behind”, “interval” | get_live_snapshot (+ describe_gap if two cars named) |
| RECENT_EVENTS | “what happened”, “last few minutes”, “miss” | summarize_recent_events |
| DRIVER_INFO | “who is #17”, “about car 22” | driver_card |
| STRATEGY | “pit”, “fuel”, “stop” | predict_pit_window (fallback) |
| INCIDENT | “why crash/penalty” | search_corpus + propose_penalty (stub) |
| GENERAL_RULE | “rules”, “penalty for” | search_corpus |

## 8. Embeddings Strategy
- Brute-force cosine similarity in-memory for small corpus.
- SQLite embeddings table: (doc_id INTEGER PRIMARY KEY, dim INT, vector BLOB, norm REAL).
- Rebuild index incrementally when new/updated doc hash differs.
- Future: optional pluggable backend (pgvector) via env flag.

## 9. Configuration (Environment Variables)
| Variable | Description | Default |
|----------|-------------|---------|
| NATS_URL | nats server url | nats://nats:4222 |
| SQLITE_PATH | path to SQLite db | /workspace/data/agent.db |
| OPENAI_API_KEY | embedding API key (if using OpenAI) | (unset) |
| EMBEDDING_MODEL | model name | text-embedding-3-small |
| LOG_LEVEL | logging level | INFO |
| MCP_PORT | MCP JSON-RPC over HTTP (optionally) | 8000 |
| MCP_STDIO_ONLY | if “1” skip HTTP server | 0 |
| SNAPSHOT_POS_HISTORY | frames to keep | 900 |
| INCIDENT_RING_SIZE | recent incidents | 300 |

## 10. Directory Layout
```
.
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── src/
│   └── sim_racecenter_agent/
│       ├── __init__.py
│       ├── config/
│       │   └── settings.py
│       ├── adapters/
│       │   └── nats_listener.py
│       ├── core/
│       │   ├── state_cache.py
│       │   ├── models.py
│       │   └── intent.py
│       ├── persistence/
│       │   └── sqlite_store.py
│       ├── embeddings/
│       │   ├── worker.py
│       │   └── index.py
│       ├── mcp/
│       │   ├── server.py
│       │   ├── registry.py
│       │   ├── resources.py
│       │   └── tools/
│       │       ├── get_live_snapshot.py
│       │       ├── summarize_recent_events.py
│       │       ├── search_corpus.py
│       │       ├── driver_card.py
│       │       ├── describe_gap.py
│       │       ├── predict_pit_window.py
│       │       └── propose_penalty.py
│       ├── director/
│       │   ├── agent.py
│       │   └── chat_listener_interface.py
│       ├── cli/
│       │   └── main.py
│       └── util/
│           ├── logging.py
│           └── timing.py
├── tests/
│   └── test_placeholder.py
├── scripts/
│   ├── init_db.py
│   └── run_mcp.py
├── data/ (gitignored)
├── pyproject.toml
├── requirements.txt
├── Makefile
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
├── README.md
└── .copilot/instructions.md
```

## 11. Initial SQLite Schema (Migration 0001)
- incidents_flat(id TEXT PRIMARY KEY, session_id TEXT, lap INT, cars TEXT, category TEXT, severity INT, ts REAL)
- documents(id INTEGER PRIMARY KEY AUTOINCREMENT, doc_type TEXT, session_id TEXT, chunk_idx INT, text TEXT, hash TEXT, updated_at REAL)
- embeddings(doc_id INT PRIMARY KEY, dim INT, vector BLOB, norm REAL)
- driver_stats(driver_id TEXT PRIMARY KEY, name TEXT, car_number INT, starts INT, wins INT, avg_finish REAL, incidents_per_hour REAL, updated_at REAL)
- summaries(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, kind TEXT, content TEXT, created_at REAL)
- answers_log(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, question TEXT, answer TEXT, tools TEXT, created_at REAL)
- faq_pairs(hash TEXT PRIMARY KEY, question TEXT, answer TEXT, last_used_at REAL, usage_count INT)

## 12. Tool Response Consistency
All tools MUST:
- Include schema_version
- Include generation timestamp (ISO8601) if they synthesize
- Avoid embedding large arrays if not requested
- Keep numeric fields normalized (seconds as float, laps integer)

## 13. Logging & Metrics
Structured JSON logs (logger name: component). Track:
- tool.call: {tool, duration_ms, success, cache_hit, error?}
- ingest.event: {stream, subject, seq, size_bytes, latency_ms?}
- embeddings.update: {doc_id, dim, duration_ms}
- director.answer: {intent, length, tools, latency_total_ms}

## 14. Testing Strategy
- Unit tests: state_cache logic, intent classification, vector similarity.
- Integration (mock NATS): feed synthetic events & assert tool outputs stable.
- CLI smoke: scripts/init_db.py then scripts/run_mcp.py (dry-run).

## 15. Dev Container Goals
- Reproducible environment with Python 3.12
- Preinstalled dev deps: pytest, black, isort, mypy, ruff, pre-commit
- NATS CLI optional (debug)
- Task workflow: `make dev`, `make test`, `make format`, `make run-mcp`

## 16. Future Extensions
- Operator WebSocket server
- Penalty precedent mining
- Advanced strategy modeling (fuel, tires)
- External vector DB switch
- Authorization & RBAC for operator actions
- Multi-session historical analytics (DuckDB / Postgres)

## 17. Copilot Implementation Guidance
When generating code:
1. Follow spec directory layout.
2. Use dependency injection via simple Settings object.
3. Keep tools pure + side-effect free except reading caches.
4. Validate tool inputs with pydantic.
5. Provide docstrings & type hints.
6. Avoid large synchronous JetStream pulls during tool calls (do in background).
7. Expose an async `run_all()` orchestrator in scripts/run_mcp.py for local dev.

## 18. Minimal MVP Definition (v0.1)
Must include:
- Dev container
- Settings loader
- NATS listener skeleton (no real subjects required yet – placeholder)
- State cache with dummy update API
- MCP server with get_live_snapshot (returns stub) & search_corpus (returns empty set)
- Director agent stub that echoes recognized LEADER queries
- Basic embedding worker placeholder
- init_db script creating schema

## 19. Non-Goals (v0.1)
- Real penalty classification
- Real pit strategy
- Full transcript ingestion
- Production-grade auth

## 20. Acceptance Checklist (for initial PR)
- `docker compose up --build` brings up devcontainer (or open in VS Code)
- `make init-db` creates database with all tables
- `make run-mcp` starts MCP server & logs ready state
- `pytest` passes (placeholder tests)
- `ruff` / `black` produce no diffs
- `mypy` runs with no blocking errors (allow “warn return any” at start)

---
End of Spec (v0.1)
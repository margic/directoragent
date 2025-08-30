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

### Components (Single Process Runtime)
The agent embeds a single FastMCP server over stdio. All tools are decorator‑registered async functions in a single module for simplicity:
   - `mcp.sdk_server`: FastMCP instance + decorated tools (`get_live_snapshot`, `get_current_battle`, `get_fastest_practice`, `get_roster`, `get_session_history`, `search_chat`, `search_corpus`).
   - `adapters.nats_listener`: Lifespan task pushing NATS messages into the shared `StateCache`.
   - `core.state_cache`: In‑memory race context (telemetry, standings, timing, incidents, pits, history).
   - `director.agent`: LLM planner + tool executor (stdio MCP client only – HTTP removed).
   - `director.chat_responder`: Consumes chat, invokes planner, publishes answers.

Legacy HTTP / JSON-RPC shim code has been fully removed. Future operator UIs can attach via a separate process if needed.

## 3. Data Sources & Persistence (Phase 1)
| Data Type              | Source          | Storage Mechanism               | Retention Strategy            |
|------------------------|-----------------|---------------------------------|------------------------------|
| Position snapshots (1Hz)| JetStream (RACE.POSITIONS) | In-memory ring buffer (900 frames) | 15 min window |
| Incidents              | JetStream (RACE.INCIDENTS) | Deque (300 recent) + SQLite incidents_flat | Full session persisted |
| Events (fastlap, battle)| JetStream (RACE.EVENTS)    | Deque (200 recent)              | 30–60 min |
| Session lifecycle       | JetStream (RACE.SESSION)   | Current session context          | Archive final summary |
| Summaries (partial)     | JetStream (RACE.SUMMARIES) | Keep last 10 + SQLite summaries  | Full session |
-------------------+           +--------------------+
| Driver stats            | Computed post-session      | SQLite driver_stats              | Cumulative |
| Transcripts / docs      | External ingestion (future)| SQLite documents + embeddings    | All |
-------------------+           |  - FastMCP Server  |
| Rules/FAQ               | Seed files / manual        | SQLite (faq_pairs) + local YAML  | All |
| Embeddings              | Derived                    | SQLite embeddings + in-memory matrix | Rebuild on change |

## 4. Tooling (Current Decorator-Based Set)
All tools return dicts augmented by `add_meta()` (`schema_version`, `generated_at`).

1. `get_live_snapshot` – Composite snapshot: session_state, track_conditions, truncated standings & lap timing, recent incidents/pits (bounded), roster size, driver preview.
2. `get_current_battle` – Closest proximity pairs from telemetry (inputs: `top_n_pairs`, `max_distance_m`).
3. `get_fastest_practice` – Fastest lap & top N cars (from lap_timing or standings fallback) with gaps.
4. `get_roster` – Condensed roster (CarIdx, car number, name) + count.
5. `get_session_history` – Recent session_state changes (bounded `limit`).
6. `search_chat` – FTS over ingested chat messages (optional username/day filters).
7. `search_corpus` – Multi-scope lexical search (`rules`, `chat`) with per-scope hit counts & error map.

Deferred / Removed stubs: `summarize_recent_events`, `propose_penalty` (await richer event & penalty data streams).

## 5. MCP Resources (Phase 1)
- live/leaderboard.json
- live/incidents_recent.json
- live/events_recent.json
- live/session_meta.json
- cache/rolling_summary.json (latest partial summary)
- driver/{driver_id}.json (generated on-demand)
## 23. Increment 0.1c – Extended iRacing Data Contract (Cross‑Project)

Objective: Formalize a versioned subject & JSON payload contract between the publisher (pyracing / telemetry producer) and this Agent for higher‑value race context (standings, gaps, lap timing, session state, incidents, pit events, track conditions, driver status, fuel/tire). Enables restoration of full LEADER/GAP intents, richer strategy stubs, and narrative tools.

- rules/penalties.md (placeholder)
- faq/popular.json

## 6. Director Agent Flow (Single Process)

Operational Flow (LLM Planning + Answer Synthesis):
1. Chat message arrives (YouTube live stream context; moderate volume, high value per answer).
2. Planner prompt (Gemini) receives tool catalog and message; returns JSON plan: [{name, arguments}].
3. Empty / invalid plan => message ignored (noise suppression, cost control).
4. Agent executes each allowed tool via in-process stdio MCP client (errors -> {error:"tool_failed"}).
5. Answer prompt (Gemini) receives original message + tool result JSON; returns `{"answer": str}`.
6. Agent enforces hard 200 char cap and returns answer; otherwise ignores.

Rationale (Live Stream Focus):
- YouTube channel chat rate is low enough that higher per‑message latency is acceptable.
- Prioritizes authoritative, contextual answers; avoids brittle keyword heuristics.
- Natural suppression of low‑signal chatter (no plan -> no reply) keeps stream clean.
- Adding tools only requires updating the planner prompt (no intent routing code).
- Safety: LLM never executes tools directly—agent validates tool names and arguments first.

Configuration (Agent environment):
- `LLM_PLANNER_MODEL` (env) -> `Settings.llm_planner_model` (default gemini-2.5-flash)
- `LLM_ANSWER_MODEL` (env) -> `Settings.llm_answer_model` (default gemini-2.5-flash)
(All prior heuristic / dual-mode flags removed.)

Implementation Summary:
   - `scripts/run_agent.py` launches NATS ingestion + chat responder; spawns MCP stdio server automatically.
   - `director/agent.py` performs plan -> execute -> synthesize over stdio MCP.
   - `director/reasoning.py` supplies planning and answer prompts.
   - `config/settings.py` centralizes model + NATS subject config.

Error Handling & Safeguards:
- Missing API key or failed planner call => silent ignore (prevents low-quality fallback).
- Tool failures surfaced minimally in JSON; answer model instructed not to invent absent fields.
- Length cap applied post-generation.

Planned Enhancements:
- Structured logging: (message, plan JSON, timings, answer) for quality iteration.
- Rate limit + dedupe cache.
- Optional moderation / filter pass before emission.

Security Notes:
- Only sanitized tool outputs passed to LLM.
- Planner output filtered to registered tool names before execution.

## 7. (Deprecated) Intent Heuristic Table
Historical heuristic routing removed. The planner LLM now selects tools solely from the catalog; no static keyword mapping remains. Table retained only for archival context.

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
| MCP_SERVER_CMD | override server spawn command | (internal default) |
| SNAPSHOT_POS_HISTORY | frames to keep | 900 |
| INCIDENT_RING_SIZE | recent incidents | 300 |

## 10. Directory Layout (Updated)
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
│       │   └── sdk_server.py        # FastMCP server + all decorated tools (single file)
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
│   ├── run_mcp.py            # (Deprecated stub or removed)
│   ├── run_agent.py          # Agent process (NATS ingestion + chat responder)
│   ├── respond_chat.py       # Chat responder only
│   ├── ingest_chat.py        # Persist chat messages into SQLite
│   ├── ingest_sporting_code.py
│   └── chat_tester.py        # Interactive NATS chat test client
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

- Unit tests: state_cache logic, intent classification, vector similarity.
- Integration (mock NATS): feed synthetic events & assert tool outputs stable.
- CLI smoke: scripts/init_db.py then scripts/run_agent.py (spawns MCP stdio and answers locally).

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
7. (Removed) Previous `run_all()` orchestrator and separate HTTP launcher scripts (now single stdio process).

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

---

## 21. Increment 0.1a – Workable Initial Use Case (Current Publisher Data Only)

This incremental slice narrows scope to ONLY the data fields verifiably published today by the existing `pyracing` publisher / emulator: per‑driver telemetry frames with proximity distances and periodic session driver roster snapshots. It defers richer leaderboard / incident / event streams until publisher enhancements land.

### 21.1 Available Data (Confirmed)
From `iracing.telemetry` (per driver frame, subset):
- `driver_id`, `display_name`, `CarIdx`, `CarNumber`
- `CarDistAhead`, `CarDistBehind` (meters to nearest car ahead/behind if known)
- `CarNumberAhead`, `CarNumberBehind` (string car numbers of those nearest cars)
- Optional `_emulator` flag (set by telemetry emulator)

From `iracing.session` (periodic snapshot):
- `drivers`: list of `{ driver_id, display_name, CarNumber }`
- `timestamp`
- Optional `_emulator` flag

Not yet available (and therefore out of scope in 0.1a answers): authoritative race order / positions, interval gaps in seconds, pit stop counts, incidents, events, lap numbers, session flag state.

### 21.2 Adjusted MVP Tooling
Maintain existing `get_live_snapshot` (stub) but add a NEW tool focused on current value:

1. `get_current_battle` (NEW)
    - Input: `{ "top_n_pairs"?: int=1, "max_distance_m"?: float=50.0 }`
    - Logic: Aggregate latest telemetry per driver, extract candidate proximity pairs from (CarDistAhead, CarNumberAhead) and (CarDistBehind, CarNumberBehind). Normalize unordered pairs, keep minimal distance for duplicates, filter where `distance_m <= max_distance_m`, sort ascending, return top N.
    - Output:
       ```json
       {
          "schema_version": 1,
          "generated_at": "2025-08-23T12:34:56Z",
          "pairs": [
             {
                "focus_car": "11",
                "other_car": "22",
                "distance_m": 8.4,
                "relation": "ahead",        
                "driver": "Driver A",
                "other_driver": "Driver B"
             }
          ],
          "roster_size": 5,
          "emulator": true
       }
       ```
    - Notes: If no qualifying pairs, return empty `pairs` array.

2. (Optional minor enhancement) `get_live_snapshot` MAY include `roster_size` and a truncated `drivers` list (first N) using session snapshot roster, but SHOULD NOT claim authoritative ordering.

### 21.3 State Cache Additions
- Add a telemetry map: `latest_by_driver: dict[str, TelemetryFrame]` where `TelemetryFrame` stores only needed keys (driver_id, display_name, CarNumber, CarDistAhead, CarDistBehind, CarNumberAhead, CarNumberBehind, updated_at, emulator: bool).
- Provide accessor used by `get_current_battle`.

### 21.4 Director Agent – Incremental Intents
Supported intents in 0.1a:
- `LEADER` (temporarily reinterpreted as *roster lead / first listed driver*): Answer with first driver from session roster (or "No drivers yet").
- `BATTLE` (NEW): Triggers `get_current_battle(top_n_pairs=1)`. Answer formats:
   - If battle: `Closest battle: Car 11 vs 22 – 8.4m gap.` (Include driver names if <200 chars.)
   - If none: `No close battles (<50m) among N cars.`

Intent keyword additions: `battle`, `close`, `who's close`, `closest`. (Add to classifier heuristic.)

### 21.5 Answer Constraints
- Global limit: 200 characters.
- Distances: retain one decimal (round half up). Meter unit implied; append `m`.
- Do not invent gaps in seconds (until numeric speed / interval data available).

### 21.6 Acceptance Criteria (Increment 0.1a)
| ID | Criterion |
|----|-----------|
| A1 | Subscribing adapter ingests `iracing.telemetry` & updates per-driver cache. |
| A2 | Subscribing adapter ingests `iracing.session` & updates roster cache. |
| A3 | `get_current_battle` tool callable via MCP; returns deterministic pair ordering for synthetic inputs. |
| A4 | Director returns valid battle answer when a pair distance < 50m exists; otherwise fallback message. |
| A5 | All tool responses include `schema_version` & ISO8601 `generated_at`. |
| A6 | Answers never exceed 200 chars (truncate gracefully if needed). |
| A7 | Emulator frames flagged -> tool sets `emulator: true` when any included pair came from emulator data OR all frames currently emulator. |
| A8 | Empty telemetry state yields clear, non-error responses (no exceptions). |

### 21.7 Future Step After 0.1a
Next planned enhancement (0.1b) once publisher supplies standings snapshot: introduce true `leaderboard` tool (or upgrade `get_live_snapshot`) with ordered positions + gap seconds, enabling restoration of original LEADER / GAP intent semantics, then layer incidents/events ingestion.

---

## 22. Increment 0.1b – Live NATS Ingestion (Telemetry + Session + Chat)

Objective: Move from synthetic / test-fed caches to live consumption of published subjects documented in `docs/nats-messages.md` – specifically `iracing.telemetry`, `iracing.session` (ephemeral) and JetStream `youtube.chat.message` – persisting chat to SQLite and updating in-memory proximity telemetry + roster for tools.

### 22.1 Subjects & Handling
| Subject | Persistence | Action |
|---------|-------------|--------|
| iracing.telemetry | Ephemeral | Parse JSON frame per message; extract subset fields (driver_id/display_name/CarNumber + CarDistAhead/CarDistBehind/CarNumberAhead/CarNumberBehind) and call `StateCache.upsert_telemetry_frame()` |
| iracing.session | Ephemeral | Replace roster via `StateCache.update_roster(drivers)`; mark timestamp; may clear stale telemetry for drivers no longer present |
| youtube.chat.message | JetStream (pull) | Already ingested via `scripts/ingest_chat.py` for persistence + FTS (`chat_messages`); additionally expose optional in-process async task variant for unified runtime |

### 22.2 Adapter Implementation
File: `src/sim_racecenter_agent/adapters/nats_listener.py`
Responsibilities:
1. Establish NATS connection (re-use existing `NATS_URL`).
2. Simple core subscriptions (async callbacks) for telemetry & session subjects.
3. Lightweight JSON parse with defensive error handling (ignore malformed frames, log once per error type per minute).
4. Metrics counters (future) – for now, print debug lines optionally gated by `LOG_LEVEL`.
5. Provide `run_telemetry_listener(cache: StateCache, stop_event: asyncio.Event)` coroutine.

Chat ingestion remains a separate JetStream pull worker script for robustness (can run independently & backfill). Later we may embed an optional mode.

### 22.3 Failure / Backoff Strategy
* Connection loss: attempt reconnect with exponential (cap 30s). During downtime, tools keep serving last cached state.
* Telemetry decode error: skip message; do not crash loop.
* Session update with zero drivers: retain previous roster until a non-empty snapshot arrives (prevents flicker).

### 22.4 Minimal Telemetry Field Normalization
Incoming frame keys (see `nats-messages.md`) are more expansive; we only store:
```
{
   "driver_id": frame.get("driver_id") or frame.get("display_name"),
   "display_name": frame.get("display_name") or frame.get("driver_id"),
   "CarNumber": frame.get("CarNumber"),
   "CarDistAhead": frame.get("CarDistAhead"),
   "CarDistBehind": frame.get("CarDistBehind"),
   "CarNumberAhead": frame.get("CarNumberAhead"),
   "CarNumberBehind": frame.get("CarNumberBehind")
}
```
All other raw keys are ignored until needed by new tools.

### 22.5 Director Impact
`get_current_battle` will now reflect live proximity data. No tool schema change required.

### 22.6 Acceptance Criteria (Increment 0.1b)
| ID | Criterion |
|----|-----------|
| B1 | HTTP + REST shim removed; stdio MCP auto-spawned inside agent. |
| B2 | Receiving a telemetry message updates internal `_telemetry` map (verified by injecting synthetic NATS publish in test). |
| B3 | Receiving a session snapshot replaces roster; battle tool reflects new roster size. |
| B4 | System tolerates malformed JSON (logged, no crash). |
| B5 | Chat ingestion script continues to persist JetStream messages (no regression). |
| B6 | Spec documents subjects used & retained subset fields (this section). |

### 22.7 Out of Scope
* Full incident/event ingestion
* Embedding generation
* Advanced metrics & structured logging (placeholder print only)

---
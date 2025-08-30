# Technology Stack Overview

Status: INITIAL (v0.1) – Single reference point for core + planned technologies.

## 1. Runtime & Language
- Python 3.12 (asyncio for concurrent NATS + MCP + background tasks)
- Type Hints + Pydantic (validation)
- Packaging: `pyproject.toml` (PEP 621) + `requirements.txt` (runtime pin mirror)

## 2. Core Services & Messaging
| Concern | Technology | Purpose | Notes |
|---------|-----------|---------|-------|
| Pub/Sub + Streaming | NATS JetStream | Telemetry, session, chat (future incidents) | Reconnect & backoff logic required |
| MCP Transport | stdio (FastMCP) | Tool invocation protocol | Single-process embedding of server |

## 3. Persistence Layer
| Store | Usage | Features |
|-------|-------|----------|
| SQLite (file) | Chat messages, FAQ pairs, embeddings, summaries, driver stats, logs | FTS5 tables for search; simple BLOB vectors |
| In-memory StateCache | Telemetry, roster, timing, incidents (future) | O(1) reads for tool latency |

## 3.1 Containerization & Dev Environment
- Dev Container: VS Code / Dev Containers setup defines a reproducible Python 3.12 environment with tooling preinstalled (pytest, ruff, black, mypy, pre-commit).
- Runtime Deployment: Intended to run inside a container (Docker) alongside a NATS service (via `docker-compose.yml`).
- Design Assumptions:
	- All external services accessed via network (NATS, LLM API, future Discord / YouTube endpoints).
	- No reliance on host-specific paths; SQLite path configurable via `SQLITE_PATH` env. Container env ok.
	- Container image should be minimal (runtime + deps) with optional dev layer for build/test.
- Future: Multi-container split (agent core, operator UI, embeddings worker) once complexity warrants.


## 4. LLM & AI Components
| Role | Current Model | Notes |
|------|---------------|-------|
| Planner | Gemini 2.5 Flash (env-config) | Returns JSON plan (tool list + args) |
| Answer Generator | Gemini 2.5 Flash | Enforces brevity + context-only answers |
| Future Summarizer | TBD (same family or cheaper model) | Digest mode & high-volume summaries |
| Embeddings | text-embedding-3-small (OpenAI optional) | Local fallback: stub until integration |

Safeguards: tool allowlist filter, max tool count, length cap, schema_version tagging.

## 5. Retrieval & Search
- SQLite FTS5: `chat_messages_fts`, `documents_fts` (sporting code / rules).
- Lexical search tools: `search_chat`, `search_corpus`.
- Future: hybrid lexical + vector rerank once embeddings stable.

## 6. Tooling & Developer Experience
| Tool | Purpose |
|------|---------|
| pytest | Unit & integration tests |
| ruff | Linting & import order |
| black | Formatting |
| mypy | Static type analysis |
| pre-commit | Consistent hooks |
| Makefile targets | `make test`, `make format`, `make run-mcp`, `make init-db` |

## 7. Observability (Planned)
- Structured logs (JSON) with: message_id, intent, plan_tools, tool_latency_ms, answer_chars.
- Metrics counters (in-process) for: tool_success, tool_error, planner_fail, publish_success.
- Future export: simple `/metrics` HTTP or push gateway.

## 8. Voice & Real-Time Interfaces (Planned)
| Component | Technology | Status |
|-----------|-----------|--------|
| Driver Voice Relay | Discord bot + TTS (service TBD, e.g., ElevenLabs / Amazon Polly) | Planned (UC-103) |
| Operator Alerts | Discord DM / UI dashboard | Planned |

## 9. Security & Config
- Environment variables (see spec §8) manage credentials / endpoints.
- No secrets committed; SQLite file local, not remote accessible.
- Future: token rotation & limited-scope keys for publishing chat messages.

## 10. Architectural Principles
1. Tool-Centric: All data-access & analytics via MCP tools (auditable, testable contracts).
2. Deterministic JSON: `schema_version`, `generated_at` unify downstream parsing.
3. Fail-Silent Bias: Prefer suppression over speculative / hallucinated answers.
4. Incremental Extensibility: Add tools & prompts without core refactor.
5. Minimal Stateful Memory: Keep bounded context to control token costs.

## 11. Integration Matrix
| Function | Dep | Degradation Behavior |
|----------|-----|----------------------|
| Battle detection | StateCache telemetry | Empty list if stale/empty |
| Chat search | SQLite FTS | Returns empty hits w/ error code (fts_missing) |
| Corpus search | SQLite FTS | Same as above |
| Planner | LLM API | Silence if error/timeouts |
| Answer | LLM API | Silence or fallback notice (config) |
| Publish to chat | YouTube API | Retry then drop (log) |

## 12. Future Considerations
- Circuit breaker for LLM failures (UC-106).
- Rate-aware batching (UC-102) and digest summarization (UC-104).
- Alerting layer for moderation & escalation (UC-105).
- Vector search integration for semantic rule / FAQ retrieval.

## 13. Related Documentation
| Doc | Purpose |
|-----|---------|
| `spec.md` | High-level specification & architecture |
| `use_cases.md` | Detailed AI agent behaviors (UC-100+) |
| `api_mcp_tools.md` | Tool schemas & contracts |
| `business_logic_rules.md` | Operational decision rules |
| `success_metrics.md` | KPIs definitions |
| `rules/penalties.md` | Future penalties taxonomy |
| `fastmcp_design_patterns.md` | Project-specific FastMCP server & tool registration patterns |
| `mvp_v1_definition.md` | MVP v1 scope, dispositions & E2E test matrix |

---
Feedback / additions welcome; update this file when introducing new infra or moving components out-of-process.

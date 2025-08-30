# MVP v1 Definition

Status: DRAFT (proposed)  
Audience: Engineering / QA / Product (what must ship together for a credible first production livestream)

## 1. Purpose
Codify the exact feature scope, acceptance criteria, and end‑to‑end (E2E) test expectations for MVP v1 of the Sim RaceCenter AI Director. Consolidates all documented use cases (UC‑100+ high‑level agent flows plus UC‑001..012 legacy granular cases) and classifies them as: In‑Scope (Full), In‑Scope (Foundational Slice), or Deferred (Post‑v1). Provides a test matrix and exit criteria for go‑live.

## 2. Scope Summary (High-Level)
| Capability | Use Case IDs | MVP v1 Disposition | Notes |
|------------|--------------|--------------------|-------|
| Real-Time Chat Monitoring & Intent Determination | UC-100 | In-Scope (Full) | Planner + suppression + loop prevention |
| Multi-Turn Contextual Answering | UC-101 | In-Scope (Foundational) | Memory of last K Q/A only; no advanced coreference ML |
| Adaptive Batching & Combined Responses | UC-102 | Deferred (Phase v1.x) | Rate monitor stub only (metrics) |
| Voice Relay (Discord) | UC-103 | Deferred | Text answer events emitted; no TTS |
| High-Volume Digest Summarization | UC-104 | Deferred | Instrument chat rate only |
| Director Priority Alerts | UC-105 | Deferred | Basic logging of trigger conditions only |
| Degradation & Fallback Handling | UC-106 | In-Scope (Foundational) | Circuit breaker counters + silence policy (no fallback message) |
| Chat Response Publication & Attribution | UC-107 | In-Scope (Full) | Rate limiting + duplicate suppression |
| Battle Detection Queries | UC-001 + get_current_battle | In-Scope (Full) | Distance threshold + ordering |
| Session Snapshot Queries | UC-002 + get_live_snapshot | In-Scope (Foundational) | Partial snapshot fields only |
| Fastest Practice Inquiry | UC-003 + get_fastest_practice | In-Scope (Foundational) | Top N; gaps vs leader |
| Roster Listing | UC-004 + get_roster | In-Scope (Full) | Count + names subset |
| Rules / Sporting Code Lookup | UC-005 + search_corpus | In-Scope (Foundational) | Lexical FTS only (no semantic rerank) |
| Chat History Reference | UC-006 + search_chat | In-Scope (Full) | FTS + result summarization |
| Noise Suppression | UC-007 | In-Scope (Full) | Planner empties -> silence |
| Tool Catalog Extensibility | UC-008 | In-Scope (Foundational) | Single registry pattern + tests |
| Penalty Suggestion | UC-009 | Deferred | No propose_penalty tool yet |
| Recent Events Summarization | UC-010 | Deferred | summarize_recent_events tool absent |
| Operator Oversight (Answer Audit) | UC-011 | Deferred | Logging only; no UI |
| Embedding Refresh Worker | UC-012 | Deferred | Stub worker maintained |

Legend:  
Full = Complete functional path with acceptance criteria.  
Foundational = Minimal viable subset enabling future iteration (documented constraints).  
Deferred = Explicitly out of MVP v1; not blocking release.

## 3. Functional Requirements (Condensed)
### 3.1 Core Chat Flow
1. Ingest YouTube chat line -> filter self-authored -> normalize.
2. Planner LLM returns JSON array plan or invalid; invalid => silence.
3. Execute tools sequentially (bounded ≤5).
4. Answer LLM synthesizes ≤200 character response strictly from tool JSON.
5. Publication validator enforces: not duplicate of last 5 answers, not empty, within length, passes restricted phrase filter.
6. Rate limiter: at most 1 answer / 3s (configurable) outside potential future busy mode.

### 3.2 Tool Determinism
- Every tool returns schema_version + generated_at (if synthesized) + stable key set.
- Empty logical result sets produce valid empty arrays/objects (never raw nulls mid-structure).

### 3.3 Memory (Foundational)
- Retain last K (default 10) answered Q/A pairs + associated tool outputs (hash + timestamp) for potential reuse in UC‑101.
- Provide age cutoff (e.g., 5 minutes) beyond which entries ignored.

### 3.4 Degradation Handling (Foundational)
- Timeouts (planner or answer) => silence; increment error counters.
- Consecutive planner failures >= N (default 3) opens circuit: skip planner for 30s; still log messages.
- Circuit auto-closes after cooldown unless failures persist.

### 3.5 Publication
- Duplicate detection: Levenshtein distance or exact match? MVP: exact string match vs last 5 answers.
- Backpressure: If answer produced while circuit is open for publications (auth error), drop and log (no retry storm).

### 3.6 Search Tools
- FTS queries limit results to ≤10 internal rows; summarizer selects top relevant snippet(s) and compresses.
- No semantic ranking; purely lexical bm25 ordering.

### 3.7 Battle Tool
- Distance filtered by max_distance_m (default 50); pairs sorted ascending distance; support top_n_pairs (default 3, max 5). Partial results allowed.

### 3.8 Snapshot Tool (Foundational)
- Provide (if present): session_name, lap, total_laps?, driver_count, top_standings[] (≤10). Missing fields omitted.

## 4. Non-Functional Targets
| Dimension | Target | Measurement Plan |
|-----------|--------|------------------|
| Chat Answer Latency p95 | < 2.5s | Instrument planner+answer timing; sample 100+ messages |
| Tool Call Latency p95 | < 150ms | Time each handler | 
| Planner Failure Rate | < 5% during steady state | Count/time window |
| Tool Error Rate | < 2% | Success vs error envelopes |
| Silence Precision | ≥ 85% (fraction of silences that were truly low-value) | Manual label sample |
| Duplicate Answer Rate | < 1% of published | Compare normalized answer set |
| Circuit Breaker False Open | 0 in acceptance run | Simulated failures |

## 5. E2E Test Matrix (Representative)
| Test ID | Title | Flow Covered | Priority | Type |
|---------|-------|-------------|----------|------|
| E2E-001 | Battle Query Answer | UC-100 + UC-001 | P0 | Chat->Plan->Tool->Answer->Publish |
| E2E-002 | No Battle -> Silence | UC-007 + UC-001 | P0 | Suppression correctness |
| E2E-003 | Roster Query | UC-004 | P0 | Snapshot tool path |
| E2E-004 | Rules Lookup | UC-005 | P0 | FTS corpus search |
| E2E-005 | Chat History Reference | UC-006 | P1 | FTS chat + summarization |
| E2E-006 | Fastest Practice | UC-003 | P1 | Lap timing/gap formatting |
| E2E-007 | Planner Invalid JSON | UC-100 / UC-007 | P0 | Error -> silence |
| E2E-008 | Tool Failure Degradation | UC-106 | P0 | Failure increments counters; silence |
| E2E-009 | Circuit Breaker Open/Close | UC-106 | P1 | Forced failures -> open -> cooldown recovery |
| E2E-010 | Duplicate Answer Suppression | UC-107 | P1 | Publish once, second identical suppressed |
| E2E-011 | Rate Limiting | UC-107 | P1 | 3 rapid valid queries -> only first within window published |
| E2E-012 | Multi-Turn Follow-up | UC-101 | P2 | Second message referencing prior answer |
| E2E-013 | Memory Stale Drop | UC-101 | P2 | Follow-up after staleness threshold -> treated standalone |
| E2E-014 | Snapshot Missing Data Resilience | UC-002 | P2 | Partial cache -> still answers |
| E2E-015 | Search No Results | UC-005/006 | P2 | Valid empty response formatting |

Priorities: P0 (must pass pre‑release), P1 (must pass before go‑live unless waived), P2 (can trail but desirable).

## 6. Sample Gherkin Scenarios
### 6.1 Battle Query (E2E-001)
```
Scenario: Answer a battle query with closest pair
  Given telemetry cache contains drivers 11 and 22 separated by 8.4 meters
    And max_distance_m is 50
    And top_n_pairs default is 1
  When a user chat message arrives with text "Who is battling right now?"
  Then the planner produces a plan including get_current_battle
    And the tool returns one pair (11,22) with distance 8.4
    And the answer model outputs a string containing "11 vs 22" and "8.4m"
    And the publication layer posts exactly one message to chat within 2.5 seconds
```

### 6.2 Planner Invalid JSON (E2E-007)
```
Scenario: Planner returns malformed JSON -> silence
  Given a chat message "Who leads?"
    And the planner call times out or returns non-JSON text
  When the agent processes the message
  Then no tool executions occur
    And nothing is published
    And a planner_failure counter increments by 1
```

### 6.3 Circuit Breaker (E2E-009)
```
Scenario: Repeated planner failures open and close circuit
  Given the failure threshold is 3
  And the cooldown is 30 seconds
  When 3 consecutive planner calls fail
  Then the circuit state becomes OPEN
  And subsequent chat messages within 30 seconds bypass planner and are silently suppressed
  When 30 seconds elapse without new failures
  Then the circuit state becomes CLOSED
```

### 6.4 Duplicate Answer Suppression (E2E-010)
```
Scenario: Prevent immediate duplicate answer
  Given the agent published the answer "Closest battle: 11 vs 22 – 8.4m"
  And this answer is still within the duplicate window (last 5 answers)
  When an identical query arrives producing the same candidate answer
  Then the answer is not published
    And a duplicate_suppressed counter increments
```

### 6.5 Multi-Turn Follow-up (E2E-012)
```
Scenario: Short pronoun follow-up uses memory
  Given a first message "Who is leading now?" answered with "Car 11 leads by 1.2s"
  And this Q/A is stored in memory
  When a subsequent message "How far ahead are they now?" arrives within 2 minutes
  Then planner context includes the prior answer summary
    And the selected tools either reuse existing data if < staleness threshold or re-run
```

## 7. Test Data & Environment
- Use deterministic seed fixtures for telemetry (static snapshot for battle & fastest lap scenarios).
- SQLite test DB ephemeral (tmp path) initialized via `init_db` script.
- Mock/stub LLM layer returning canned planner plans and answer JSON for deterministic tests; separate integration tests may hit real model behind feature flag.
- Time control: employ freezetime or monotonic clock injection to simulate cooldowns & staleness.

## 8. Tool / Layer Test Coverage Expectations
| Layer | Coverage Expectation |
|-------|----------------------|
| Tool Handlers | ≥95% statements for deterministic logic |
| Planner Wrapper | Key branches (success, timeout, invalid JSON) |
| Publication Layer | Rate limit, duplicate, success, failure paths |
| Circuit Breaker | Threshold open, cooldown close |
| Memory Store | Insert, retrieval, staleness eviction |

## 9. Exit Criteria (Go-Live Gate)
All P0 & P1 E2E tests pass in CI twice consecutively.  
Non-functional latency targets met on synthetic load sample (≥50 messages).  
No open Sev1 / Sev2 defects linked to in-scope capabilities.  
Documentation updated: `spec.md` (version), `api_mcp_tools.md` (any schema bumps), `fastmcp_design_patterns.md` (if patterns changed).  
Operational Runbook draft exists (basic start/stop, env vars, log interpretation).  

## 10. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM latency spikes | Breach latency SLO | Add timeout + early silence; consider model fallback |
| Planner JSON drift | Silent suppression false positives | Add JSON schema validation & fuzz tests |
| Rate limiter misconfig | Under/over answering | Config sanity test & default safe limits |
| Circuit breaker false opens | Reduced responsiveness | Tune thresholds; add debug metrics view |
| Duplicate detection too strict | Legit answers suppressed | Start with exact match only |

## 11. Post-v1 Backlog (Deferred Items)
- Implement adaptive batching (UC‑102) + digest summarization (UC‑104).
- Discord voice relay (UC‑103) w/ priority classifier.
- Alert taxonomy & UI integration (UC‑105).
- Penalty inference tool (UC‑009) and events summarization (UC‑010).
- Semantic reranking & embeddings refresh workflow (UC‑005, UC‑006 enhancement, UC‑012 realization).

## 12. Traceability Matrix (Use Case -> Tests)
| Use Case | Primary E2E Tests |
|----------|------------------|
| UC-100 | E2E-001, E2E-007, E2E-011 |
| UC-101 | E2E-012, E2E-013 |
| UC-102 | (Deferred) |
| UC-103 | (Deferred) |
| UC-104 | (Deferred) |
| UC-105 | (Deferred) |
| UC-106 | E2E-008, E2E-009 |
| UC-107 | E2E-010, E2E-011 |
| UC-001 | E2E-001, E2E-002 |
| UC-002 | E2E-014 |
| UC-003 | E2E-006 |
| UC-004 | E2E-003 |
| UC-005 | E2E-004, E2E-015 |
| UC-006 | E2E-005, E2E-015 |
| UC-007 | E2E-002, E2E-007 |
| UC-008 | (Covered by unit/contract tests; no direct E2E) |
| UC-009 | (Deferred) |
| UC-010 | (Deferred) |
| UC-011 | (Deferred) |
| UC-012 | (Deferred) |

---
Update this document whenever MVP criteria, dispositions, or test matrix changes.

# High-Level Use Cases

Status: DRAFT (v0.1) – working document to elaborate richer end‑to‑end scenarios beyond the brief user stories in the spec.

## Format Legend
Each use case follows this structure:

# AI Director Agent Use Cases (Chat & Context Focus)

Status: DRAFT – Replaces prior generic examples; concentrates on higher‑level agent behaviors: contextual chat understanding, adaptive summarization, and voice relay.

## Format
Each use case lists: ID, Title, Primary Actor(s), Stakeholders, Trigger, Pre‑Conditions, Post‑Conditions, Main Flow, Extensions, Metrics, Supporting Components, Open Questions.

---
## UC-100 Real-Time Chat Monitoring & Intent Determination
**Primary Actor:** AI Director Agent  
**Stakeholders:** Race Director (human), Stream Audience, Streaming Driver  
**Trigger:** Any new YouTube chat message arrives.  
**Pre-Conditions:** Chat ingest pipeline active; planner LLM reachable; tool registry loaded.  
**Post-Conditions:** Message is (a) classified with an actionable intent and queued for response, or (b) suppressed with rationale (low signal / duplicate / off-topic).  
**Main Flow:**
0. Ingest raw message.
1. Author self-check: if author == configured agent/brand account (e.g., "Sim RaceCenter") then: persist to chat history ONLY (for archival / context) and STOP (no planner call) – prevents response loops.
2. Normalize (strip, language detect (TODO), dedupe hash).
3. Lightweight pre-filter (regex / rate heuristics) optionally drops spam.
4. Planner prompt built with rolling short context window (last N relevant Q&A and active race state summary).
5. Planner returns JSON plan (tools + answer strategy flag: single|batch|defer).
6. Valid plan -> dispatch to execution pipeline; else suppression.
**Extensions:**
E1: Planner timeout -> fallback heuristic (very limited) or suppression.  
E2: Tool limit exceeded (>5) -> truncate plan.  
E3: Detected duplicate question in recent window -> mark as duplicate; optionally coalesce answers.  
E4: Self-authored message incorrectly passes filter (misconfigured account name) -> secondary guard before publish drops emission if author == agent.
**Metrics:** Intent Classification Recall, Silence Precision, Planner Latency, Token Cost / msg.  
**Components:** Chat Ingest, Planner LLM, StateCache, Tool Registry.  
**Open Questions:** Introduce light classifier ahead of planner to reduce LLM calls?  

---
## UC-101 Multi-Turn Contextual Answering
**Primary Actor:** AI Director Agent  
**Trigger:** User follow-up referencing previous answer (pronouns / ellipsis).  
**Pre-Conditions:** Conversation state store retains last K (question, answer, tool results) tuples with timestamps.  
**Post-Conditions:** Follow-up resolved using earlier context or agent requests clarification (future).  
**Main Flow:**
1. New message -> coreference / ellipsis detector (e.g., contains "that", "them", or short pronoun-only query).  
2. If flagged, retrieve last relevant answer + tool outputs summary; embed in planner context block.  
3. Planner may reuse earlier tool results if still fresh (staleness < configurable threshold) or schedule re-run.  
4. Answer LLM crafts contextually aware reply.  
**Extensions:**
E1: Stale data -> force tool refresh.  
E2: Prior context ambiguous -> (future) ask user to clarify (currently likely suppression).  
**Metrics:** Follow-up Resolution Rate, Context Reuse Ratio, Stale Answer Incidents.  
**Components:** Conversation Memory Store, Freshness Policy, Planner.  
**Open Questions:** Memory size vs token budget; semantic clustering of prior Qs.  

---
## UC-102 Adaptive Batching & Combined Responses
**Primary Actor:** AI Director Agent  
**Trigger:** Chat message arrival while message rate > adaptive threshold (e.g., > X msgs / 30s).  
**Pre-Conditions:** Sliding rate counter implemented.  
**Post-Conditions:** Related questions consolidated; single synthesized answer posted after short aggregation delay.  
**Main Flow:**
1. Rate monitor flags "busy" state.  
2. Incoming Qs added to topic clustering buffer (lexical / embedding).  
3. Every T seconds (e.g., 7s) cluster heads produce one plan (union of required tools).  
4. Execute minimal tool set; produce batched answer summarizing shared info & enumerating key variants.  
**Extensions:**
E1: Rate drops below threshold -> flush buffers immediately.  
E2: Conflicting intents (battle + rules) -> split into two answers but still batched.  
E3: Tool execution error for one sub-intent -> degrade answer noting omission or omit silently.  
**Metrics:** Batch Consolidation Ratio, Average Latency (busy mode), Token Savings %, User Satisfaction (survey).  
**Components:** Rate Monitor, Topic Clustering, Batch Scheduler, Planner, Tool Executor.  
**Open Questions:** Optimal aggregation window vs perceived responsiveness.  

---
## UC-103 Voice Relay to Driver (Discord Race Voice Channel)
**Primary Actor:** AI Director Agent  
**Stakeholders:** Streaming Driver, Spotter / Director.  
**Trigger:** (a) High-priority chat item (e.g., safety concern, penalty query), or (b) periodic summarized digest interval.  
**Pre-Conditions:** Discord bot authenticated & connected to race voice channel; TTS service available.  
**Post-Conditions:** Driver hears concise spoken summary; avoids cognitive overload mid-race.  
**Main Flow:**
1. Classify message priority (battle change, crucial rule clarification, streamer-directed question).  
2. For high priority: generate short voice-friendly phrasing (remove user handles, abbreviate units).  
3. Synthesize speech -> stream to Discord voice channel.  
4. Log relay event (text, timestamp, duration).  
**Extensions:**
E1: TTS failure -> fallback to text-only log; optionally retry once.  
E2: Channel rate limiting -> queue with max age; discard stale.  
E3: Driver mute command -> suspend voice relay until re-enabled.  
**Metrics:** Relay Latency, Priority Recall, Driver Interrupt Satisfaction.  
**Components:** Priority Classifier, Voice Formatter, TTS Client, Discord Bot.  
**Open Questions:** Dynamic adaptation to driver workload (e.g., skip during intense battles).  

---
## UC-104 High-Volume Chat Summarization (Digest Mode)
**Primary Actor:** AI Director Agent  
**Trigger:** Chat throughput sustained above threshold for Y seconds.  
**Pre-Conditions:** Summarization model or prompt template; rolling chat buffer retained.  
**Post-Conditions:** Periodic digest message (e.g., every 60s) summarizing key themes, questions still unanswered, and notable events, while individual low-value messages suppressed.  
**Main Flow:**
1. Enter "digest mode" when sustained rate condition met.  
2. Collect messages into minute buckets with lightweight categorization (questions / reactions / hype / off-topic).  
3. At interval boundary, build summary prompt with counts + top N representative Qs.  
4. Publish condensed summary; reset bucket.  
**Extensions:**
E1: Sudden lull -> exit digest mode early.  
E2: Critical question arrives mid-interval -> bypass digest for immediate answer.  
E3: Token budget exceeded -> truncate categories by priority.  
**Metrics:** Digest Coverage %, Token Savings, User Retention delta, Critical Question Delay.  
**Components:** Rate Monitor, Category Tagger, Summarizer LLM, Scheduler.  
**Open Questions:** Automatic adjustment of interval length based on entropy of topics.  

---
## UC-105 Director Priority Alerts
**Primary Actor:** AI Director Agent  
**Stakeholders:** Human Race Director / Stream Operator.  
**Trigger:** Detection of pattern requiring human review (repeated rule disputes, potential harassment, high incident frequency).  
**Pre-Conditions:** Basic classification of message categories + incident feed (future).  
**Post-Conditions:** Alert delivered (console log / future UI / Discord DM) with concise rationale and recommended action.  
**Main Flow:**
1. Aggregate signals (e.g., ≥3 rule questions about same clause within 2 min).  
2. Create alert object (type, count, last_examples, suggested_tool).  
3. Dispatch to alert channel; mark as active until cleared or timed out.  
**Extensions:**
E1: Duplicate active alert -> increment counter only.  
E2: Alert channel unreachable -> persist for later replay.  
**Metrics:** Mean Time To Awareness (MTTA), False Alert Rate, Action Follow-through %.  
**Components:** Signal Aggregator, Alert Dispatcher, Persistence.  
**Open Questions:** Severity scoring & escalation policy.  

---
## UC-106 Degradation & Fallback Handling
**Primary Actor:** AI Director Agent  
**Trigger:** Planner or answer model failure; tool execution errors; DB unavailable.  
**Pre-Conditions:** Health checks & circuit breaker counters.  
**Post-Conditions:** System degrades gracefully (silence, partial cached answer, or minimal textual fallback) without flooding chat.  
**Main Flow:**
1. Detect error condition (timeout, auth error, repeated tool failure).  
2. Increment error counter; possibly open circuit (skip planner for next N seconds).  
3. Provide fallback (e.g., “Data updating, please retry shortly.”) only if user directly asked; else silence.  
4. Expose status to monitoring hook.  
**Extensions:**
E1: Recovered health -> close circuit & resume normal responses.  
E2: Prolonged outage > threshold -> escalate alert (UC-105).  
**Metrics:** Error Containment Ratio, Circuit Open Duration, User Complaint Rate.  
**Components:** Circuit Breaker, Health Monitor, Minimal Fallback Templates.  
**Open Questions:** When to prefer stale cached answer vs silence.  

---
## UC-107 Chat Response Publication & Attribution (YouTube Persona)
**Primary Actor:** AI Director Agent  
**Stakeholders:** Stream Audience, Streaming Driver, Race Director  
**Trigger:** A prepared answer (single or batched) passes validation (length, safety, non-duplication) and is ready for emission.  
**Pre-Conditions:**
 - Agent has an authenticated channel identity (YouTube API key / OAuth token) for the Sim RaceCenter account.
 - Loop prevention filter (UC-100) active to ignore self-authored messages.
 - Rate limit & flood control thresholds loaded (e.g., max 1 message / 3s normal; relaxed in digest mode).  
**Post-Conditions (Success Guarantees):**
 - Answer is posted to live chat attributed to Sim RaceCenter.
 - Message stored in local chat history / answers_log with metadata (tools_used, latency_ms, batch_id?).
 - Publication metrics updated (per-intent counters).  
**Main Flow:**
1. Planner + tools produce answer candidate.
2. Publication validator checks: non-empty, <=200 chars, UTF-8 clean, no disallowed phrases, not duplicate of last K (configurable) answers.
3. Rate limiter consulted (global + intent-specific buckets). If over limit, queue or drop (config policy).
4. Post via YouTube Live Chat API (or existing NATS->publisher bridge if indirect).
5. Persistence: insert row into `answers_log` (question, answer, tools, timestamps, persona_id="SimRaceCenter").
6. Emit internal event (e.g., `agent.answer.published`) for monitoring / voice relay (UC-103) pipeline.
**Extensions / Alternate Flows:**
E1: API transient failure -> retry with exponential backoff (max 2 attempts) then abort silently.  
E2: Hard auth error (401/403) -> open circuit; stop publishing and raise Director Priority Alert (UC-105).  
E3: Rate limit (429) -> schedule delayed publish if still relevant (freshness window < 15s) else drop.  
E4: Duplicate detection triggers -> skip publish, maybe increment duplicate counter.  
E5: Safety filter flags potential policy violation -> log & suppress (do not attempt sanitized rewrite automatically in MVP).  
**Metrics / KPIs:** Publish Success Rate, Mean Publish Latency, Duplicate Skip Ratio, Rate-Limit Deferrals, Auth Incident Count.  
**Supporting Components:** Answer Validator, Rate Limiter, YouTube Publisher Adapter, Answers Log Store, Event Bus (internal).  
**Open Questions:**
 - Exact freshness window for deferred (rate-limited) answers.
 - Should batch summaries identify they are aggregated (prefix)?
 - Mechanism to override suppression (manual force publish?).  

---
## Open Gaps
- Need concrete Gherkin scenarios for UC-100, UC-101, UC-102, UC-104, UC-106.
- Define precise rate thresholds & hysteresis (busy mode enter/exit) – TBD.
- Discord voice relay technical spec (auth, reconnection, latency budget) – TBD.
- Clarify privacy / moderation considerations for voice relays (filter sensitive content).  

## Next Steps
1. Assign metric owners & baseline measurement approach.
2. Prototype rate monitor + batching (UC-102, UC-104 shared components).
3. Define memory schema for multi-turn context (UC-101) including staleness logic.
4. Draft alert taxonomy (UC-105) & severity scoring matrix.
5. Implement circuit breaker instrumentation (UC-106) with thresholds.

  - Director agent running; planner model reachable.
- Post-Conditions:
  - (Success) Chat receives a concise answer naming the closest pair within threshold.
  - (Failure) No answer emitted (silent) if no pairs satisfy threshold or planner produces empty plan.
- Main Flow:
  1. Chat message ingested.
  2. Planner produces plan: [{ name: get_current_battle, args: { top_n_pairs: 1 } }].
  3. Tool executes; returns closest pair list (≤1).
  4. Answer model formats: “Closest battle: Car 11 vs 22 – 8.4m gap.”
  5. Message published (≤200 chars).
- Extensions:
  - E1: No proximity pairs → Answer: “No close battles (<50m) among N cars.”
  - E2: Tool failure → Return minimal error JSON; answer model instructed to omit hallucination; likely silence.
  - E3: Planner empty/invalid → Silent suppression.
- Metrics: Answer Accuracy, Latency p95, Silence Precision, Battle Detection Freshness.
- Tools: get_current_battle.
- Open Questions: Adaptive threshold? Multi-battle summarization variant.

## UC-002 Session Context Snapshot
- Primary Actor: Viewer
- Trigger: Generic context query (“What’s going on now?”)
- Pre-Conditions: Snapshot tool available; partial data ok.
- Post-Conditions: Viewer gets high-level summary (future once answer patterns codified) OR silence if planner not confident yet.
- Main Flow (future enriched): plan -> get_live_snapshot -> formatted key elements.
- Extensions: Missing data fields gracefully omitted.
- Metrics: Coverage, Accuracy.
- Tools: get_live_snapshot.
- Open Questions: Summary template definition; prioritization of what fits into 200 chars.

## UC-003 Fastest Practice Inquiry
- Primary Actor: Viewer
- Trigger: Query about fastest lap (“Who’s quickest?”)
- Pre-Conditions: Lap timing OR standings fallback available.
- Main Flow: plan -> get_fastest_practice(top_n=3) -> answer with leader + gap(s).
- Extensions: No lap data -> fallback message.
- Metrics: Accuracy, Latency.
- Tools: get_fastest_practice.
- Open Questions: Represent ongoing improvements (delta vs previous fastest?).

## UC-004 Roster Listing
- Primary Actor: Viewer / New entrant
- Trigger: Query “Who’s in?” / “How many drivers?”
- Main Flow: plan -> get_roster -> answer includes count + first few names.
- Extensions: Empty roster → “No drivers yet.”
- Metrics: Coverage.
- Tools: get_roster.

## UC-005 Rules / Sporting Code Lookup
- Primary Actor: Viewer / Moderator
- Trigger: “What’s the rule for blue flags?”
- Main Flow: plan -> search_corpus(scopes=["rules"], limit=5) -> answer summarizing top snippet.
- Extensions: FTS missing -> silence or error-cautious fallback.
- Metrics: Accuracy, Tool Error Rate.
- Tools: search_corpus.
- Open Questions: Introduce semantic rerank once embeddings stable.

## UC-006 Chat History Reference
- Primary Actor: Viewer / Moderator
- Trigger: “What did they say about pit stops earlier?”
- Main Flow: plan -> search_chat(query, limit=5) -> synthesized short answer referencing count or a key message.
- Extensions: Empty results -> answer “No prior messages matching ‘pit’.”
- Metrics: Retrieval Precision.
- Tools: search_chat.

## UC-007 Noise Suppression
- Primary Actor: System
- Trigger: Low-signal / off-topic message.
- Main Flow: Planner outputs empty or non-tool plan -> agent suppresses response.
- Metrics: Silence Precision, Token Cost Savings.
- Tools: (Planner only)
- Open Questions: Add lightweight heuristic pre-filter to save planning tokens.

## UC-008 Tool Catalog Extensibility
- Primary Actor: Developer
- Trigger: Need to add new analytic (e.g., incident frequency).
- Main Flow: Implement tool -> register in sdk_server -> adjust planner prompt -> tests.
- Metrics: Mean time to add tool, Regression Rate.
- Tools: (n/a) This is a process use case.
- Open Questions: Auto-generate planner tool summary from JSON Schemas.

## UC-009 Penalty Suggestion (Planned)
- Primary Actor: Viewer / Moderator
- Trigger: “Should that be a penalty?” after an incident.
- Pre-Conditions: Incident event stream & rule taxonomy available.
- Main Flow (future): plan -> propose_penalty(context window) -> answer with rationale + uncertainty disclaimers.
- Metrics: Suggestion Precision, False Positive Rate.
- Tools: propose_penalty (DEFERRED), search_corpus.

## UC-010 Recent Events Summarization (Planned)
- Primary Actor: Viewer
- Trigger: “What happened in the last few laps?”
- Main Flow: plan -> summarize_recent_events(window=300) -> answer with 1–2 sentence narrative.
- Metrics: Informativeness, Brevity Compliance.
- Tools: summarize_recent_events (DEFERRED).

## UC-011 Operator Oversight (Future)
- Primary Actor: Operator / Streamer
- Trigger: Need to audit answer history for quality.
- Main Flow: Query answers_log table via future operator UI.
- Metrics: Review Throughput, Issue Detection Rate.
- Tools: (Database + future UI components).

## UC-012 Embedding Refresh (Background)
- Primary Actor: System
- Trigger: New documents ingested / FAQ updated.
- Main Flow: Worker recalculates embeddings for changed docs; updates SQLite; invalidates in-memory cache.
- Metrics: Embedding Freshness SLA.
- Tools: embeddings.worker (placeholder).

---
## Template For New Use Cases
```
## UC-XXX Title
- Primary Actor:
- Stakeholders:
- Trigger:
- Pre-Conditions:
- Post-Conditions:
- Main Flow:
- Extensions:
- Metrics:
- Tools:
- Open Questions:
```

---
## Open Gaps
- Formal acceptance criteria not yet attached to each use case (only increments cover A/B sets).
- Need Gherkin-style scenarios for battle tool, roster, search reliability.
- Add data freshness guarantees (staleness thresholds) per tool.

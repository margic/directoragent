# Success Metrics (Placeholder)

Status: TODO – instrumentation not yet implemented.

| Metric | Definition | Target | Instrumentation Plan |
|--------|------------|--------|----------------------|
| Answer Accuracy | % of sampled answers judged correct | >=85% | Manual labeling sample (weekly) -> future automated rubric |
| Chat Coverage | Answered race-relevant questions / total questions | Balanced (TBD) | Tag questions via heuristic or manual review |
| Latency p95 | Planner + tool exec + answer generation | <2.5s | Timing envelope per message (structured logs) |
| Tool Error Rate | Failed tool calls / total tool calls | <2% | Aggregate error counters |
| Silence Precision | % of suppressed messages truly low value | >=90% | Post-hoc labeling set |
| Battle Detection Freshness | Time since telemetry frame used (sec) | <2s | Compare now - frame.updated_at |

## Roadmap
1. Add structured logging fields (message_id, timings_ms, tools_invoked, answer_chars).
2. Export counters via simple /metrics HTTP (future) or log scraping.
3. Dashboard (Grafana or lightweight panel) once metrics stable.

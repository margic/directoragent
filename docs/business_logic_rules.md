# Business Logic Rules (Placeholder)

Status: PARTIAL – consolidated rules for Director decisions and content emission.

## Director Decision Logic
1. If planner output is empty or invalid JSON -> no response.
2. Only execute tools whose names are in the registered allowlist.
3. Parallel tool execution optional later; currently sequential to simplify ordering.
4. If any tool fails, include minimal error object; do not fabricate missing fields.
5. After answer generation, enforce 200 char cap; if answer is empty after trimming -> drop.

## Content Generation Rules
- Distances: show 1 decimal meter precision.
- Avoid speculative gaps/time deltas until authoritative data available.
- Prefer driver display_name; fallback to CarNumber; final fallback "Unknown".
- Never expose raw internal IDs unless user explicitly asks for debugging.

## Safety / Suppression
- Offensive / irrelevant chat (future moderation filter) -> planned suppression stage.
- Planner anomalies (tool flooding, > N tools) -> truncate to first N (config default 5).

## TODO
- Add penalty inference heuristics once incidents + rules codified.
- Specify prioritization when multiple battles present (currently distance ascending then car number tiebreak).

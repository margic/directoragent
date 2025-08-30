# Penalties & Rules (Planned Placeholder)

Status: PLANNED – to be filled during Increment 0.1c when incident + flag + pit data streams become available.

## Objectives
- Enumerate rule infractions relevant to automated penalty suggestion.
- Map incident telemetry/events to candidate rule breaches.
- Provide structured precedent data for future ML classification.

## Proposed Data Points
- Incident type (contact, off-track, unsafe rejoin, pit speeding)
- Lap / session timestamp
- Involved drivers (ids, car numbers)
- Severity heuristic (low/med/high)
- Outcome (spin, damage, no-loss)

## Next Steps
1. Define canonical incident event schema from publisher.
2. Create rule taxonomy (code -> description -> severity bounds).
3. Implement minimal penalty inference stub returning rationale strings.

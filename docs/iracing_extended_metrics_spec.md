# iRacing Extended Metrics & Events Specification

Version: 0.1 (Draft)
Date: 2025-08-24
Status: PARTIALLY IMPLEMENTED (Phases 1–3 complete; enrichment/predictive items pending)
Owner: Telemetry / Data Layer

## Purpose
Define additional high‑value racing data feeds derived from iRacing telemetry + session info to power richer overlays, analytics, commentary, and strategy features while keeping the core `iracing.telemetry` subject lean.

## Guiding Principles
- Additive & backward compatible (never break existing subjects).
- Separate subjects by concern (standings, timing, events, strategy) for selective subscription.
- Event subjects are emitted only on change to minimize bandwidth.
- Computations kept O(N) per update; heavy aggregations deferred to consumers.
- JetStream persistence only where historical replay / audit is valuable (incidents & pit events).

## Subject Overview (with Implementation Status)
| Subject | Type | Cadence / Trigger | Persistence | Status | Notes |
|---------|------|-------------------|-------------|--------|-------|
| iracing.standings | Snapshot array | 1–2 Hz | Ephemeral | IMPLEMENTED | Live publishing. |
| iracing.lap_timing | Aggregated subset | 1 Hz | Ephemeral | IMPLEMENTED | Top N + focus car. |
| iracing.session_state | Snapshot object | On change / 1 Hz max | Ephemeral + JetStream (IRACING_HISTORY 14d) | IMPLEMENTED | Persisted timeline. |
| iracing.incident | Event | Counter increase | JetStream (IRACING_EVENTS 7d) | IMPLEMENTED | JetStream audit. |
| iracing.pit | Event | Pit entry/exit | JetStream (IRACING_EVENTS 7d) | IMPLEMENTED | Includes duration & fuel. |
| iracing.track_conditions | Snapshot object | Threshold / ≥5s debounce | Ephemeral | IMPLEMENTED | Change-driven thresholds. |
| iracing.stint | Lap boundary snapshot | Pit exit + each lap | Ephemeral + JetStream (IRACING_HISTORY 14d) | IMPLEMENTED | Strategy history persisted. |
| iracing.driver_status | Per-car delta | On change / 1 Hz max | Ephemeral | PENDING | Planned enrichment. |
| strategy.projection (future) | Projection | Recompute 5–10s | TBD (likely JetStream) | PENDING | Fuel window / next stop. |

## 1. iracing.standings
Frequency: 1–2 Hz (configurable)
Payload:
```jsonc
{
  "timestamp": "ISO8601",
  "leader_car_idx": 12,
  "cars": [
    {"car_idx":12, "pos":1, "class_pos":1, "lap":120, "gap_leader_s":0.0, "gap_ahead_s":null, "last_lap_s":68.432},
    {"car_idx":7,  "pos":2, "class_pos":2, "lap":120, "gap_leader_s":1.287, "gap_ahead_s":1.287, "last_lap_s":68.500},
    {"car_idx":3,  "pos":3, "class_pos":1, "lap":119, "gap_leader_s":5.612, "gap_ahead_s":4.325, "last_lap_s":68.910}
  ]
}
```
Derivations:
- `gap_leader_s = estTime(car) - estTime(leader)` using `CarIdxEstTime`.
- `gap_ahead_s` is difference to previous car in sorted position list.
- Sort cars where `CarIdxPosition > 0`.

## 2. iracing.lap_timing
Frequency: 1 Hz.
Two modes:
- Per-car messages (simpler consumer filtering) OR
- Aggregated subset array (top N + focus car). Start with aggregated.
Payload (aggregated):
```jsonc
{
  "timestamp": "ISO8601",
  "cars": [
    {"car_idx":12, "lap":120, "last_lap_s":68.432, "best_lap_s":68.201, "current_lap_time_s":25.321, "delta_best_s":0.231},
    {"car_idx":7,  "lap":120, "last_lap_s":68.500, "best_lap_s":68.333, "current_lap_time_s":25.410, "delta_best_s":0.299}
  ]
}
```
Fields:
- `delta_best_s = current_lap_time_s - best_lap_s` if still on same lap & data valid.
Fallback if some lap metrics not present (use null).

## 3. iracing.session_state
Trigger: Any change in session type, time remaining (delta > 1s), flag bits, pits open state, pace mode.
Payload:
```jsonc
{
  "timestamp": "ISO8601",
  "session_type": "RACE",      // from SessionInfo latest session entry
  "time_remaining_s": 1423.5,    // computed from session length - elapsed
  "flag_bits": 1024,             // raw CarIdxSessionFlags leader or player
  "caution": true,
  "green": false,
  "pits_open": true,
  "pace_mode": 2
}
```
Flag interpretation requires mapping `irsdk_Flags` bit constants.

## 4. iracing.incident (Event)
Trigger: Player or any tracked car incident counter increases.
Payload:
```jsonc
{
  "timestamp": "ISO8601",
  "car_idx": 12,
  "delta": 2,
  "total": 12,
  "team_total": 34
}
```
Persist via JetStream: Stream `IRACING_EVENTS`, subject `iracing.incident`.

## 5. iracing.pit (Event)
Triggers & payloads:
- Entry (transition `OnPitRoad` false -> true):
```jsonc
{"timestamp":"ISO8601","event":"enter","car_idx":12,"lap":120}
```
- Exit (transition true -> false):
```jsonc
{"timestamp":"ISO8601","event":"exit","car_idx":12,"lap":120,"stop_duration_s":18.432,"fuel_added_l":27.5,"fast_repair_used":false}
```
Stream: `IRACING_EVENTS`, subject `iracing.pit` (JetStream).
`stop_duration_s` measured between entry & exit timestamps. `fuel_added_l` from diff in fuel level across stop (if fuel variable present). Fast repair usage inferred by `FastRepairUsed` increment.

## 6. iracing.track_conditions
Frequency: Every 30 s OR earlier if any watched value changes beyond thresholds.
Payload:
```jsonc
{
  "timestamp":"ISO8601",
  "air_temp_c": 23.4,
  "air_pressure_pa": 101325,
  "air_density": 1.22,
  "track_temp_c": 31.8,
  "fog_pct": 0.0,
  "precip_pct": null
}
```
Thresholds (suggested):
- Air / track temp change > 0.5°C
- Air pressure change > 200 Pa
- Fog level change > 1%

## 7. iracing.driver_status
Trigger: Any change for tracked car in position, class position, pit road status, track surface, class id (debounced to 1 Hz max).
Payload (per car):
```jsonc
{
  "timestamp":"ISO8601",
  "car_idx":12,
  "pos":1,
  "class_pos":1,
  "on_pit_road":false,
  "track_surface":2,
  "class_id":5
}
```
Could batch an array variant; start per-car to ease debouncing.

## 8. iracing.stint
Events at pit exit + lap boundary (for active / focus car or all if desired).
Payload:
```jsonc
{
  "timestamp":"ISO8601",
  "car_idx":12,
  "lap":121,
  "fuel_level_l":45.3,
  "fuel_pct":0.54,
  "avg_fuel_lap_l":2.41,
  "est_laps_remaining":18.8,
  "stint_laps":11,
  "tire_wear_pct":{
    "LF":{"L":82.1,"M":80.5,"R":81.3},
    "RF":{"L":83.4,"M":82.2,"R":81.9},
    "LR":{"L":84.7,"M":83.9,"R":83.1},
    "RR":{"L":85.0,"M":84.2,"R":83.5}
  }
}
```
Derivations:
- `avg_fuel_lap_l` rolling average since stint start (ignore formation laps if needed).
- `est_laps_remaining = fuel_level_l / avg_fuel_lap_l` (null until avg stabilizes >= 2 laps).
- Tire wear slots from LFwearL/M/R etc. If not all available, include subset.

## JetStream Configuration (Current Streams)
| Stream | Subjects | Retention | Purpose |
|--------|----------|-----------|---------|
| YOUTUBE_CHAT | youtube.chat.message | 14 days | Chat replay & moderation. |
| IRACING_EVENTS | iracing.incident, iracing.pit | 7 days | Discrete race event history. |
| IRACING_HISTORY | iracing.session_state, iracing.stint | 14 days | Session & strategy timeline. |

Potential additions (evaluation): track_conditions trends, strategy.projection outputs.

## Implementation Roadmap & Status
Phase 1 – Core snapshots – COMPLETED
- standings, session_state, lap_timing

Phase 2 – Events – COMPLETED
- pit, incident (JetStream IRACING_EVENTS)

Phase 3 – Strategy Foundations – COMPLETED
- stint (fuel/tire metrics) with history persistence
- track_conditions (threshold emission)

Phase 4 – Enrichment & Predictive – PENDING / IN PROGRESS
- driver_status subject
- license/iRating extraction
- sector splits (investigate availability)
- strategy projections (fuel window, pit delta modeling)
- advanced pit strategy forecasting (undercut/overcut scenarios)

## Data Collection Additions
Add to telemetry variable list if missing: `TrackTemp`, `FuelLevel`, `FuelLevelPct`, `FuelUsePerHour`, `LFwearL/M/R`, `RFwearL/M/R`, `LRwearL/M/R`, `RRwearL/M/R`, `CarIdxEstTime`, `CarIdxPosition`, `CarIdxClassPosition`, `OnPitRoad`, `FastRepairUsed`.

## Error & Edge Handling
- Missing variables: send field as null; log once (suppress repeats).
- Gaps when leader laps a car: negative gaps clipped to >= 0; lap difference can be appended later.
- Reconnect: flush in-memory caches (previous values); emit fresh session_state immediately.
- Large fields: cap `cars` array length (e.g., top 40) if message size approaches 64KB.

## Security / Safety
- No PII beyond driver names already published in existing session roster.
- Consumers must not rely on ordering of JSON object keys.

## Versioning
- Include optional header `"spec_version":"0.1"` in each extended message (future addition). For now omitted to keep payload small.

## Open Questions / Future Work
- Sector splits variable availability & accuracy.
- Driver status granularity vs embedding into standings.
- Strategy projection subject schema & cadence.
- License / iRating enrichment from session YAML.
- Rolling fastest lap announcements (new subject vs lap_timing augmentation).
- Track condition trend analytics & optional persistence.
- Incident classification (off-track vs contact types).

---
END OF SPEC

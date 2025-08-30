# Data Models (Placeholder)

Status: PARTIAL – this document will enumerate and version core entities used by MCP tools and internal state.

## Entities

### TelemetryFrame
- driver_id: str
- display_name: str
- CarNumber: str | int
- CarDistAhead: float | null
- CarDistBehind: float | null
- CarNumberAhead: str | null
- CarNumberBehind: str | null
- updated_at: float (epoch seconds)
- emulator: bool (optional)

### RosterDriver
- driver_id: str
- display_name: str
- CarNumber: str | int

### BattlePair
- focus_car: str
- other_car: str
- distance_m: float
- relation: enum(ahead|behind|unknown)

### ChatMessage
- id: str
- author: str
- text: str
- created_at: float

### EmbeddingRecord
- doc_id: int
- vector: bytes (BLOB)
- dim: int
- norm: float
- updated_at: float

## Versioning
Add `schema_version` to outward facing tool responses. Increment when structure changes in a backward-incompatible manner.

## TODO
- Add Incident, PitEvent once publisher supplies streams.
- Formalize Leaderboard / Standings snapshot shape.

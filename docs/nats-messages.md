# NATS Messaging Specification

This document defines the subjects and message schemas published by the PyRacing / SimRaceCenter system.

## Index
- iracing.telemetry
- iracing.session
- youtube.chat.message (JetStream)
- system.control (commands)
- system.control.result (command results)
- Additional control event payload types
- Legacy / auxiliary subjects

---
## iracing.telemetry
Real‑time telemetry snapshots (JSON, UTF‑8). One message per publish interval.

Example subject: `iracing.telemetry`

Schema (representative – dynamic keys from iRacing SDK plus injected fields):
```
{
  "Speed": <float>,
  "Lap": <int>,
  ... other raw iRacing telemetry key/value pairs ...,
  "PlayerName": <string>,        // Resolved from drivers list
  "CarNumber": <string>,         // Player car number
  "CarIdx": <int>,               // Player car index
  "CarNumberAhead": <string?>,   // Optional; nearest car ahead
  "DriverAhead": <string?>,      // Optional; display name of nearest car ahead
  "CarNumberBehind": <string?>,  // Optional; nearest car behind
  "DriverBehind": <string?>,     // Optional; display name of nearest car behind
  "driver_id": <string>,         // Multi‑driver identifier (active driver or "Player")
  "display_name": <string>       // Friendly display name (falls back to driver_id)
}
```
Notes:
- Values are encoded as a single JSON object, then UTF‑8 bytes.
- Presence of *Ahead / *Behind keys depends on proximity calculations.
- Additional keys may be added without notice; consumers should ignore unknown keys.

---
## iracing.session
Periodic driver/session roster snapshots.

Subject: `iracing.session`

Schema:
```
{
  "drivers": [
    {
      "CarIdx": <int>,
      "UserName": <string>,
      "CarNumber": <string>,
      ... possible additional driver metadata ...
    },
    ...
  ]
}
```
Notes:
- Published on new session detection or at configured interval.
- Entire driver list replaces prior state (treat as authoritative snapshot).

---
## youtube.chat.message (JetStream)
YouTube live chat messages with 14‑day JetStream retention.

Stream: `YOUTUBE_CHAT`
Subject: `youtube.chat.message`

Schema:
```
{
  "type": "youtube_chat_message",
  "data": {
    "id": <string>,            // YouTube message id
    "username": <string>,
    "message": <string>,
    "avatarUrl": <string>,
    "timestamp": <ISO8601 string>,
    "type": <string>           // YouTube snippet.type (e.g. textMessageEvent)
  }
}
```
Notes:
- Stored via JetStream with max_age = 14 days.
- Ordering guaranteed per JetStream subject (sequence numbers) but not synchronized with telemetry subjects.

---
## system.control
Inbound control / command channel (requests). Used by CLI and overlay server.

Subject: `system.control`

Base Envelope:
```
{
  "type": <string>,            // Command/event type, e.g. "youtube.reset", "youtube.status", "youtube.discovery.complete"
  "command_id": <UUID string>, // Correlation id for result matching
  "timestamp": <ISO8601 string>,
  "data": { ... }              // Command-specific data object (may be empty {})
}
```
Common YouTube command types:
- `youtube.status` – query current YouTube chat connection
- `youtube.reset` – reset YouTube chat component
- `youtube.discovery.complete` – published after discovery providing IDs

Example youtube.discovery.complete:
```
{
  "type": "youtube.discovery.complete",
  "command_id": "<uuid>",
  "timestamp": "2025-08-24T18:40:12.345Z",
  "data": { "video_id": "<videoId>", "live_chat_id": "<chatId>" }
}
```

---
## system.control.result
Command responses correlated by `command_id`.

Subject: `system.control.result`

Schema:
```
{
  "command_id": <UUID string>,
  "success": <bool>,
  "type": <string>,        // Typically original command type with suffix, e.g. "youtube.status.result"
  "data": { ... },          // Optional result payload
  "error": <string?>        // Present when success=false
}
```

Example:
```
{
  "command_id": "d2c5b2d0-3f6e-4d4f-ae58-0b4f4c7d2b1c",
  "success": true,
  "type": "youtube.status.result",
  "data": { "connected": true, "live_chat_id": "<chatId>", "video_id": "<videoId>" }
}
```

---
## Additional Control Event Payload Types
Depending on future extensions, other `type` values may appear on `system.control`: `player.*`, `camera.*`, `overlay.*`, `broadcast.*`. Unimplemented handlers currently respond with `success=false` and an `error` explaining that the control is not implemented.

---
## Legacy / Auxiliary Subjects
- `system.control` (already documented) is also used for discovery completion broadcasts.
- Internal test/emulation scripts may publish to `iracing.telemetry` and `iracing.session` with the same schemas.

---
## Versioning & Compatibility
- Additive schema changes (new keys) should be considered non-breaking; consumers must ignore unknown fields.
- Removal or semantic change of existing keys requires coordination and version tagging.
- JetStream retention (14 days) applies only to `youtube.chat.message` stream; other subjects are standard core NATS (no persistence) unless server side policies override.

---
## Summary Table
| Subject                | Persistence | Payload Root Type | Purpose |
|------------------------|-------------|-------------------|---------|
| iracing.telemetry      | Ephemeral   | JSON object       | Real-time telemetry snapshot |
| iracing.session        | Ephemeral   | JSON object       | Driver roster snapshot |
| youtube.chat.message   | JetStream (14d) | JSON object   | Live chat messages |
| system.control         | Ephemeral   | JSON object       | Control commands |
| system.control.result  | Ephemeral   | JSON object       | Command results |

---
Generated: 2025-08-24

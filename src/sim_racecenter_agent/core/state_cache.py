from __future__ import annotations

import time
from collections import deque

from .models import Event, Incident, LeaderboardEntry, SessionMeta


class StateCache:
    def __init__(self, max_positions_history: int, incident_ring_size: int):
        self._leaderboard = []
        self._positions_history = deque(maxlen=max_positions_history)
        self._incidents = deque(maxlen=incident_ring_size)
        self._events = deque(maxlen=200)
        self.session_meta = None
        self.versions = {"positions": 0, "incidents": 0, "events": 0}
        # Latest per-driver proximity telemetry frames (current publisher subset)
        self._telemetry = {}
        self._roster = []  # last session snapshot drivers list

    # ---- Mutators (called by ingestion layer) ----
    def update_leaderboard(self, entries: list[LeaderboardEntry]):
        self._leaderboard = entries
        self.versions["positions"] += 1
        self._positions_history.append(
            {"t": time.time(), "entries": [(e.car, e.pos) for e in entries[:10]]}
        )

    def add_incident(self, incident: Incident):
        self._incidents.append(incident)
        self.versions["incidents"] += 1

    def add_event(self, event: Event):
        self._events.append(event)
        self.versions["events"] += 1

    def set_session_meta(self, meta: SessionMeta):
        self.session_meta = meta

    # Telemetry / roster (increment 0.1a)
    def upsert_telemetry_frame(self, frame: dict):
        """Store latest telemetry subset for a driver.

        Expected keys (if present): driver_id, display_name, CarNumber, CarDistAhead,
        CarDistBehind, CarNumberAhead, CarNumberBehind, _emulator.
        """
        did = frame.get("driver_id")
        if not did:
            return
        frame["updated_at"] = time.time()
        self._telemetry[did] = frame

    def update_roster(self, drivers: list[dict]):
        self._roster = drivers

    # ---- Accessors (increment 0.1a) ----
    def roster(self) -> list[dict]:
        return list(self._roster)

    def telemetry_frames(self) -> list[dict]:
        return list(self._telemetry.values())

    # ---- Accessors for tools ----
    def snapshot_leaderboard(self) -> list[dict]:
        return [
            {
                "pos": e.pos,
                "car": e.car,
                "driver_id": e.driver_id,
                "name": e.name,
                "gap": e.gap,
                "last_lap": e.last_lap,
                "pit_stops": e.pit_stops,
            }
            for e in self._leaderboard
        ]

    def recent_incidents(self, n: int = 25) -> list[dict]:
        return [
            {
                "id": inc.id,
                "lap": inc.lap,
                "cars": inc.cars,
                "category": inc.category,
                "severity": inc.severity,
                "timestamp": inc.timestamp,
            }
            for inc in list(self._incidents)[-n:]
        ]

    def recent_events(self, n: int = 25) -> list[dict]:
        return [
            {
                "id": ev.id,
                "kind": ev.kind,
                "timestamp": ev.timestamp,
                "data": ev.data,
            }
            for ev in list(self._events)[-n:]
        ]

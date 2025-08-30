from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Deque


class StateCache:
    """In-memory state aligned to publisher JSON schemas.

    Provides backward-compatible snapshot_leaderboard() for existing tools
    by projecting standings + roster mappings.
    """

    def __init__(self, _max_positions_history: int, incident_ring_size: int):  # legacy arg ignored
        # Base real-time subsets
        self._telemetry: Dict[str, Dict[str, Any]] = {}
        self._roster: List[Dict[str, Any]] = []  # session roster (CarIdx, UserName, CarNumber)

        # Extended snapshots / events
        self._standings_timestamp: float | None = None
        self._standings_list: List[Dict[str, Any]] = []
        self._lap_timing_timestamp: float | None = None
        self._lap_timing_list: List[Dict[str, Any]] = []
        self._session_state: Dict[str, Any] | None = None
        self._session_state_history: Deque[Dict[str, Any]] = deque(maxlen=100)  # recent states
        self._incident_events: Deque[Dict[str, Any]] = deque(maxlen=incident_ring_size)
        self._pit_events: Deque[Dict[str, Any]] = deque(maxlen=incident_ring_size)
        self._track_conditions: Dict[str, Any] | None = None
        self._stints: Dict[int, Dict[str, Any]] = {}
        # Live chat (recent) messages (if chat ingestion enabled)
        self._chat_messages: Deque[Dict[str, Any]] = deque(maxlen=500)

        # Derived helpers
        self._gap_leader_by_car: Dict[int, float | None] = {}
        self._car_idx_to_number: Dict[int, str] = {}
        self._car_idx_to_name: Dict[int, str] = {}

    # ---- Telemetry & Roster ----
    def upsert_telemetry_frame(self, frame: dict):
        did = frame.get("driver_id") or frame.get("display_name")
        if not did:
            return
        frame["updated_at"] = time.time()
        self._telemetry[did] = frame
        car_idx = frame.get("CarIdx")
        if isinstance(car_idx, int):
            if frame.get("CarNumber"):
                self._car_idx_to_number[car_idx] = str(frame.get("CarNumber"))
            if frame.get("display_name"):
                self._car_idx_to_name[car_idx] = str(frame.get("display_name"))

    def update_roster(self, drivers: list[dict]):
        self._roster = drivers
        for d in drivers:
            if isinstance(d.get("CarIdx"), int):
                idx = int(d["CarIdx"])  # type: ignore[arg-type]
                if d.get("CarNumber"):
                    self._car_idx_to_number[idx] = str(d.get("CarNumber"))
                if d.get("UserName"):
                    self._car_idx_to_name[idx] = str(d.get("UserName"))

    # ---- Standings ----
    def set_standings(self, timestamp: float, cars: list[dict]):
        self._standings_timestamp = timestamp
        self._standings_list = cars
        self._gap_leader_by_car = {}
        for c in cars:
            car_idx = c.get("car_idx")
            if isinstance(car_idx, int):
                self._gap_leader_by_car[car_idx] = c.get("gap_leader_s")

    # ---- Lap Timing ----
    def set_lap_timing(self, timestamp: float, cars: list[dict]):
        self._lap_timing_timestamp = timestamp
        self._lap_timing_list = cars

    # ---- Session State ----
    def set_session_state(self, state: dict):
        self._session_state = state
        stamped = dict(state)
        stamped.setdefault("_received_ts", time.time())
        self._session_state_history.append(stamped)

    # ---- Events ----
    def add_incident_event(self, event: dict):
        self._incident_events.append(event)

    def add_pit_event(self, event: dict):
        self._pit_events.append(event)

    # ---- Track Conditions ----
    def set_track_conditions(self, payload: dict):
        self._track_conditions = payload

    # ---- Stints ----
    def update_stint(self, car_idx: int | None, payload: dict):
        if car_idx is None:
            return
        self._stints[car_idx] = payload

    # ---- Chat Messages ----
    def add_chat_message(self, payload: dict):
        """Append a validated chat message payload (already schema-checked)."""
        self._chat_messages.append(payload)

    def recent_chat(self, n: int = 50) -> list[dict]:
        if n <= 0:
            return []
        return list(self._chat_messages)[-n:]

    # ---- Accessors ----
    def roster(self) -> list[dict]:
        return list(self._roster)

    def telemetry_frames(self) -> list[dict]:
        return list(self._telemetry.values())

    def standings(self) -> list[dict]:
        return list(self._standings_list)

    def lap_timing(self) -> list[dict]:
        return list(self._lap_timing_list)

    def session_state(self) -> dict | None:
        return self._session_state.copy() if self._session_state else None

    def session_state_history(self, limit: int = 10) -> list[dict]:
        if limit <= 0:
            return []
        return list(self._session_state_history)[-limit:]

    def track_conditions(self) -> dict | None:
        return self._track_conditions.copy() if self._track_conditions else None

    def recent_incidents(self, n: int = 25) -> list[dict]:
        return list(self._incident_events)[-n:]

    def recent_pits(self, n: int = 25) -> list[dict]:
        return list(self._pit_events)[-n:]

    def stint_for(self, car_idx: int) -> dict | None:
        return self._stints.get(car_idx)

    def leader(self) -> dict | None:
        if self._standings_list:
            return self._standings_list[0]
        return self._roster[0] if self._roster else None

    def gap_leader(self, car_idx: int) -> float | None:
        return self._gap_leader_by_car.get(car_idx)

    def car_number(self, car_idx: int) -> str | None:
        return self._car_idx_to_number.get(car_idx)

    # Backward-compatible projection for existing tools expecting 'leaderboard'
    def snapshot_leaderboard(self) -> list[dict]:
        if not self._standings_list:
            return []
        out: List[Dict[str, Any]] = []
        for entry in self._standings_list:
            car_idx = entry.get("car_idx")
            if not isinstance(car_idx, int):
                continue
            pos = entry.get("pos")
            gap_leader = entry.get("gap_leader_s")
            last_lap = entry.get("last_lap_s")
            out.append(
                {
                    "pos": pos,
                    "car": self._car_idx_to_number.get(car_idx) or str(car_idx),
                    "driver_id": car_idx,  # placeholder (no explicit driver id in schema)
                    "name": self._car_idx_to_name.get(car_idx),
                    "gap": gap_leader,
                    "last_lap": last_lap,
                    "pit_stops": None,
                }
            )
        return out

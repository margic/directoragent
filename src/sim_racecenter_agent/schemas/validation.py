"""JSON Schema validation helpers for NATS message payloads.

Lightweight wrapper using jsonschema. Only validates structure for newly
implemented extended metrics & event/history subjects.
"""

from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore

SCHEMA_DIR = Path(__file__).parent


@lru_cache(maxsize=64)
def _load_schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA_MAP = {
    "iracing.standings": "iracing.standings.schema.json",
    "iracing.lap_timing": "iracing.lap_timing.schema.json",
    "iracing.session_state": "iracing.session_state.schema.json",
    "iracing.incident": "iracing.incident.schema.json",
    "iracing.pit": "iracing.pit.schema.json",
    "iracing.track_conditions": "iracing.track_conditions.schema.json",
    "iracing.stint": "iracing.stint.schema.json",
    "youtube.chat.message": "youtube.chat.message.schema.json",
    "system.control": "system.control.schema.json",
    "system.control.result": "system.control.result.schema.json",
    "iracing.session": "iracing.session.schema.json",
    "iracing.telemetry": "iracing.telemetry.schema.json",
}


def validate(subject: str, payload: Dict[str, Any]) -> None:
    """Validate payload against subject schema.

    Raises jsonschema.ValidationError on failure. If jsonschema is not
    installed, this function is a no-op.
    """
    if jsonschema is None:
        return
    schema_file = SCHEMA_MAP.get(subject)
    if not schema_file:
        raise ValueError(f"No schema registered for subject {subject}")
    schema = _load_schema(schema_file)
    jsonschema.validate(instance=payload, schema=schema)


def is_valid(subject: str, payload: Dict[str, Any]) -> bool:
    try:
        validate(subject, payload)
        return True
    except Exception:
        return False


EXAMPLES: Dict[str, Dict[str, Any]] = {
    "iracing.standings": {
        "timestamp": 1735123456.123,
        "leader_car_idx": 12,
        "cars": [
            {
                "car_idx": 12,
                "pos": 1,
                "class_pos": 1,
                "lap": 45,
                "gap_leader_s": 0,
                "gap_ahead_s": 0,
                "last_lap_s": 91.234,
            },
            {
                "car_idx": 7,
                "pos": 2,
                "class_pos": 2,
                "lap": 45,
                "gap_leader_s": 1.523,
                "gap_ahead_s": 1.523,
                "last_lap_s": 91.876,
            },
        ],
    },
    "iracing.lap_timing": {
        "timestamp": 1735123457.100,
        "cars": [
            {
                "car_idx": 12,
                "lap": 46,
                "last_lap_s": 91.234,
                "best_lap_s": 90.900,
                "current_lap_time_s": 32.456,
                "delta_best_s": 1.556,
            },
            {"car_idx": 7, "lap": 46, "last_lap_s": 91.876, "best_lap_s": 91.300},
        ],
    },
    "iracing.session_state": {
        "timestamp": 1735123460.0,
        "session_type": "RACE",
        "time_remaining_s": 1200.5,
        "flag_bits": 1,
        "caution": False,
        "green": True,
        "pits_open": True,
        "pace_mode": "SINGLE",
    },
    "iracing.incident": {
        "timestamp": 1735123465.55,
        "car_idx": 12,
        "delta": 2,
        "total": 10,
        "team_total": 10,
    },
    "iracing.pit": {
        "timestamp": 1735123470.1,
        "event": "exit",
        "car_idx": 12,
        "lap": 50,
        "stop_duration_s": 32.5,
        "fuel_added_l": 21.3,
        "fast_repair_used": False,
    },
    "iracing.track_conditions": {
        "timestamp": 1735123475.0,
        "air_temp_c": 23.5,
        "air_pressure_pa": 101325,
        "air_density": 1.225,
        "track_temp_c": 31.2,
        "fog_pct": 0.0,
        "precip_pct": 0.0,
    },
    "iracing.stint": {
        "timestamp": 1735123480.2,
        "car_idx": 12,
        "lap": 55,
        "fuel_level_l": 34.2,
        "fuel_pct": 0.56,
        "avg_fuel_lap_l": 2.31,
        "est_laps_remaining": 14.8,
        "stint_laps": 10,
        "tire_wear_pct": {
            "LF": {"L": 0.92, "M": 0.90, "R": 0.91},
            "RF": {"L": 0.93, "M": 0.91, "R": 0.92},
            "LR": {"L": 0.94, "M": 0.93, "R": 0.94},
            "RR": {"L": 0.95, "M": 0.94, "R": 0.95},
        },
    },
    "youtube.chat.message": {
        "type": "youtube_chat_message",
        "data": {
            "id": "chatmsg123",
            "username": "Viewer42",
            "message": "Great pass!",
            "avatarUrl": "https://example.com/a.png",
            "timestamp": "2025-08-24T18:40:12.345Z",
            "type": "textMessageEvent",
        },
    },
    "system.control": {
        "type": "youtube.status",
        "command_id": "123e4567-e89b-12d3-a456-426614174000",
        "timestamp": "2025-08-24T18:40:12.345Z",
        "data": {},
    },
    "system.control.result": {
        "command_id": "123e4567-e89b-12d3-a456-426614174000",
        "success": True,
        "type": "youtube.status.result",
        "data": {"connected": True},
    },
    "iracing.session": {"drivers": [{"CarIdx": 12, "UserName": "Driver A", "CarNumber": "12"}]},
    "iracing.telemetry": {
        "CarIdx": 12,
        "Speed": 145.2,
        "Lap": 55,
        "PlayerName": "Driver A",
        "CarNumber": "12",
        "driver_id": "primary",
        "display_name": "Driver A",
    },
}


def example(subject: str) -> Dict[str, Any]:
    return EXAMPLES[subject]

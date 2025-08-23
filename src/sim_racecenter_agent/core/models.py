from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class LeaderboardEntry:
    pos: int
    car: int
    driver_id: str
    name: str
    gap: str
    last_lap: float | None = None
    pit_stops: int | None = None

@dataclass
class Incident:
    id: str
    session_id: str
    lap: int
    cars: list[int]
    category: str
    severity: int
    timestamp: float

@dataclass
class Event:
    id: str
    kind: str
    timestamp: float
    data: dict

@dataclass
class SessionMeta:
    id: str
    lap: int
    flag: str
    track: Optional[str]
    started_at: float
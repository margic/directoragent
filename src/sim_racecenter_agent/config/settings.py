from __future__ import annotations

import os
import json
from pathlib import Path

from pydantic import BaseModel, Field


class NATSSettings(BaseModel):
    url: str = Field(default="nats://nats:4222")
    telemetry_subject: str = Field(default="iracing.telemetry")
    session_subject: str = Field(default="iracing.session")
    username: str | None = Field(default="user")
    password: str | None = Field(default="pass")
    retry_interval: int = Field(default=5)


class Settings(BaseModel):
    nats: NATSSettings = Field(default_factory=NATSSettings)
    sqlite_path: str = Field(default="/workspace/data/agent.db")
    embedding_model: str = Field(default="text-embedding-3-small")
    log_level: str = Field(default="INFO")
    mcp_port: int = Field(default=8000)
    mcp_stdio_only: bool = Field(default=False)
    snapshot_pos_history: int = Field(default=900)
    incident_ring_size: int = Field(default=300)
    # Feature flags for extended subjects
    enable_extended_standings: bool = Field(default=True)
    enable_session_state: bool = Field(default=True)
    enable_lap_timing: bool = Field(default=True)
    enable_pit_events: bool = Field(default=True)
    enable_incident_events: bool = Field(default=True)
    enable_stint: bool = Field(default=True)
    enable_track_conditions: bool = Field(default=True)
    # JetStream catch-up
    enable_jetstream_catchup: bool = Field(default=True)
    catchup_max_incidents: int = Field(default=200)
    catchup_max_pits: int = Field(default=200)
    catchup_max_session_state: int = Field(default=1)
    catchup_max_stints: int = Field(default=300)
    # Additional catch-up for subjects not previously replayed
    catchup_max_session: int = Field(default=1)  # roster/session payload
    catchup_max_standings: int = Field(default=5)
    catchup_max_lap_timing: int = Field(default=5)
    # LLM models (planner + answer). Mode B is the only mode now.
    llm_planner_model: str = Field(default="gemini-2.5-flash")
    llm_answer_model: str = Field(default="gemini-2.5-flash")


def get_settings() -> Settings:
    # Load base from config file if present
    config_path = os.environ.get("CONFIG_PATH", "config.json")
    data: dict = {}
    p = Path(config_path)
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except Exception:
            pass  # ignore malformed file, fallback to env defaults
    # Environment overrides
    nats_block = data.get("nats", {}) if isinstance(data.get("nats"), dict) else {}
    # Apply env overrides for NATS
    if os.environ.get("NATS_URL"):
        nats_block["url"] = os.environ["NATS_URL"]
    if os.environ.get("TELEMETRY_SUBJECT"):
        nats_block["telemetry_subject"] = os.environ["TELEMETRY_SUBJECT"]
    if os.environ.get("SESSION_SUBJECT"):
        nats_block["session_subject"] = os.environ["SESSION_SUBJECT"]
    if os.environ.get("NATS_USERNAME"):
        nats_block["username"] = os.environ["NATS_USERNAME"]
    if os.environ.get("NATS_PASSWORD"):
        nats_block["password"] = os.environ["NATS_PASSWORD"]
    if os.environ.get("NATS_RETRY_INTERVAL"):
        nats_block["retry_interval"] = int(os.environ["NATS_RETRY_INTERVAL"])
    data["nats"] = nats_block

    return Settings(
        nats=NATSSettings(**data.get("nats", {})),
        sqlite_path=os.environ.get(
            "SQLITE_PATH", data.get("sqlite_path", "/workspace/data/agent.db")
        ),
        embedding_model=os.environ.get(
            "EMBEDDING_MODEL", data.get("embedding_model", "text-embedding-3-small")
        ),
        log_level=os.environ.get("LOG_LEVEL", data.get("log_level", "INFO")),
        mcp_port=int(os.environ.get("MCP_PORT", data.get("mcp_port", 8000))),
        mcp_stdio_only=os.environ.get("MCP_STDIO_ONLY", str(int(data.get("mcp_stdio_only", False))))
        == "1",
        snapshot_pos_history=int(
            os.environ.get("SNAPSHOT_POS_HISTORY", data.get("snapshot_pos_history", 900))
        ),
        incident_ring_size=int(
            os.environ.get("INCIDENT_RING_SIZE", data.get("incident_ring_size", 300))
        ),
        enable_extended_standings=os.environ.get(
            "ENABLE_EXTENDED_STANDINGS", str(int(data.get("enable_extended_standings", True)))
        )
        == "1",
        enable_session_state=os.environ.get(
            "ENABLE_SESSION_STATE", str(int(data.get("enable_session_state", True)))
        )
        == "1",
        enable_lap_timing=os.environ.get(
            "ENABLE_LAP_TIMING", str(int(data.get("enable_lap_timing", False)))
        )
        == "1",
        enable_pit_events=os.environ.get(
            "ENABLE_PIT_EVENTS", str(int(data.get("enable_pit_events", False)))
        )
        == "1",
        enable_incident_events=os.environ.get(
            "ENABLE_INCIDENT_EVENTS", str(int(data.get("enable_incident_events", False)))
        )
        == "1",
        enable_stint=os.environ.get("ENABLE_STINT", str(int(data.get("enable_stint", False))))
        == "1",
        enable_track_conditions=os.environ.get(
            "ENABLE_TRACK_CONDITIONS", str(int(data.get("enable_track_conditions", False)))
        )
        == "1",
        enable_jetstream_catchup=os.environ.get(
            "ENABLE_JETSTREAM_CATCHUP", str(int(data.get("enable_jetstream_catchup", True)))
        )
        == "1",
        catchup_max_incidents=int(
            os.environ.get("CATCHUP_MAX_INCIDENTS", data.get("catchup_max_incidents", 200))
        ),
        catchup_max_pits=int(os.environ.get("CATCHUP_MAX_PITS", data.get("catchup_max_pits", 200))),
        catchup_max_session_state=int(
            os.environ.get("CATCHUP_MAX_SESSION_STATE", data.get("catchup_max_session_state", 1))
        ),
        catchup_max_stints=int(
            os.environ.get("CATCHUP_MAX_STINTS", data.get("catchup_max_stints", 300))
        ),
        catchup_max_session=int(
            os.environ.get("CATCHUP_MAX_SESSION", data.get("catchup_max_session", 1))
        ),
        catchup_max_standings=int(
            os.environ.get("CATCHUP_MAX_STANDINGS", data.get("catchup_max_standings", 5))
        ),
        catchup_max_lap_timing=int(
            os.environ.get("CATCHUP_MAX_LAP_TIMING", data.get("catchup_max_lap_timing", 5))
        ),
        llm_planner_model=os.environ.get(
            "LLM_PLANNER_MODEL", data.get("llm_planner_model", "gemini-2.5-flash")
        ),
        llm_answer_model=os.environ.get(
            "LLM_ANSWER_MODEL", data.get("llm_answer_model", "gemini-2.5-flash")
        ),
    )

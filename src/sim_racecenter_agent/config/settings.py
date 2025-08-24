from __future__ import annotations

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    nats_url: str = Field(default="nats://nats:4222")
    sqlite_path: str = Field(default="/workspace/data/agent.db")
    embedding_model: str = Field(default="text-embedding-3-small")
    log_level: str = Field(default="INFO")
    mcp_port: int = Field(default=8000)
    mcp_stdio_only: bool = Field(default=False)
    snapshot_pos_history: int = Field(default=900)
    incident_ring_size: int = Field(default=300)


def get_settings() -> Settings:
    return Settings(
        nats_url=os.environ.get("NATS_URL", "nats://nats:4222"),
        sqlite_path=os.environ.get("SQLITE_PATH", "/workspace/data/agent.db"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        mcp_port=int(os.environ.get("MCP_PORT", "8000")),
        mcp_stdio_only=os.environ.get("MCP_STDIO_ONLY", "0") == "1",
        snapshot_pos_history=int(os.environ.get("SNAPSHOT_POS_HISTORY", "900")),
        incident_ring_size=int(os.environ.get("INCIDENT_RING_SIZE", "300")),
    )

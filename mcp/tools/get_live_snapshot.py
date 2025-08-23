from pydantic import BaseModel
from datetime import datetime
from mcp.adapters.state_cache import StateCache

class GetLiveSnapshotInput(BaseModel):
    fields: list[str] | None = None

class GetLiveSnapshotOutput(BaseModel):
    timestamp: str
    session: dict
    leaderboard: list
    flags: dict | None = None
    version: int

def register(tool_registry):
    tool_registry.register(
        name="get_live_snapshot",
        schema_version=1,
        description="Return current session + leaderboard snapshot.",
        input_model=GetLiveSnapshotInput,
        output_model=GetLiveSnapshotOutput,
        handler=handle_get_live_snapshot
    )

def handle_get_live_snapshot(args: GetLiveSnapshotInput, cache: StateCache) -> GetLiveSnapshotOutput:
    snap = cache.current_snapshot()
    return GetLiveSnapshotOutput(
        timestamp=datetime.utcnow().isoformat(),
        session=snap.session_meta,
        leaderboard=snap.leaderboard,
        flags=snap.flags,
        version=snap.version
    )
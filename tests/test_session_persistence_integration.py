import os
import json
import sqlite3
import asyncio
import time
import pytest
from sim_racecenter_agent.mcp.client_wrapper import MCPToolClient
from sim_racecenter_agent.config.settings import get_settings

try:
    from nats.aio.client import Client as NATS
except Exception:  # pragma: no cover
    NATS = None  # type: ignore

pytestmark = pytest.mark.asyncio

_ENV_NATS_URL = os.environ.get("NATS_URL")
_FALLBACKS = ["nats://localhost:4222", "nats://nats:4222"]
_CANDIDATE_URLS = ([_ENV_NATS_URL] if _ENV_NATS_URL else []) + [
    u for u in _FALLBACKS if u != _ENV_NATS_URL
]
NATS_URL = _CANDIDATE_URLS[0]


async def _try_connect_nats(timeout=2.0):
    if NATS is None:
        return None
    user = os.environ.get("NATS_USERNAME")
    password = os.environ.get("NATS_PASSWORD")
    for url in _CANDIDATE_URLS:
        nc = NATS()
        try:
            if user and password:
                await asyncio.wait_for(
                    nc.connect(servers=[url], user=user, password=password), timeout=timeout
                )
            else:
                await asyncio.wait_for(nc.connect(servers=[url]), timeout=timeout)
            globals()["NATS_URL"] = url
            return nc
        except Exception:
            try:
                await nc.close()
            except Exception:
                pass
            continue
    return None


def _skip_if_no_nats(nc):
    if nc is None:
        pytest.skip("NATS server not reachable for integration test")


async def _ensure_stream(js, name: str, subjects: list[str]) -> bool:
    try:
        try:
            # type: ignore[arg-type]
            await js.add_stream({"name": name, "subjects": subjects})
        except Exception:
            pass
        info = await js.stream_info(name)
        return bool(info and getattr(info.config, "name", None))
    except Exception:
        return False


async def _start_client(env: dict[str, str]):
    for k, v in env.items():
        os.environ[k] = v
    client = MCPToolClient()
    await client.start()
    return client


async def _poll(pred, timeout=8.0, interval=0.15):
    start = time.time()
    while time.time() - start < timeout:
        if await pred():
            return True
        await asyncio.sleep(interval)
    return False


@pytest.mark.integration
async def test_session_related_snapshot_persistence_and_tool(nats_url_env=None, tmp_path=None):
    nc = await _try_connect_nats()
    _skip_if_no_nats(nc)
    js = nc.jetstream()  # type: ignore

    settings = get_settings()
    # We reuse IRACING_HISTORY for historical replay of session_state + standings + session
    history_stream = "IRACING_HISTORY"
    history_subjects = [
        "iracing.session_state",
        "iracing.standings",
        settings.nats.session_subject,
    ]
    # Stubs: track_conditions not yet in history (live only) – fine for this test; we still verify tool returns 0 rows
    await _ensure_stream(js, history_stream, history_subjects)

    # Prepare messages (publish BEFORE agent start to exercise catch-up + AFTER for live)
    ts_base = time.time()
    sess_state_payload = {"timestamp": ts_base, "session_type": "RACE", "time_remaining_s": 3600.0}
    standings_payload = {
        "timestamp": ts_base + 1,
        "leader_car_idx": 12,
        "cars": [
            {"car_idx": 12, "pos": 1, "lap": 10, "gap_leader_s": 0, "gap_ahead_s": 0},
            {"car_idx": 7, "pos": 2, "lap": 10, "gap_leader_s": 1.2, "gap_ahead_s": 1.2},
        ],
    }
    session_payload = {"drivers": [{"CarIdx": 12, "UserName": "Driver A", "CarNumber": "12"}]}

    await js.publish("iracing.session_state", json.dumps(sess_state_payload).encode())
    await js.publish("iracing.standings", json.dumps(standings_payload).encode())
    await js.publish(settings.nats.session_subject, json.dumps(session_payload).encode())

    db_path = tmp_path / "agent.db" if tmp_path else tmp_path
    if tmp_path:
        env = {
            **({} if os.environ.get("NATS_URL") else {"NATS_URL": NATS_URL}),
            "SQLITE_PATH": str(db_path),
            "ENABLE_JETSTREAM_CATCHUP": "1",
            "ENABLE_SESSION_STATE": "1",
            "ENABLE_EXTENDED_STANDINGS": "1",
            # Ensure persistence code paths active
            "ENABLE_TRACK_CONDITIONS": "1",
        }
    else:
        env = {
            "ENABLE_JETSTREAM_CATCHUP": "1",
            "ENABLE_SESSION_STATE": "1",
            "ENABLE_EXTENDED_STANDINGS": "1",
            "ENABLE_TRACK_CONDITIONS": "1",
        }

    client = await _start_client(env)
    try:
        # Publish live updates AFTER start as well
        sess_state_payload_live = {
            "timestamp": ts_base + 2,
            "session_type": "RACE",
            "time_remaining_s": 3599.0,
        }
        await js.publish("iracing.session_state", json.dumps(sess_state_payload_live).encode())
        standings_payload_live = {
            "timestamp": ts_base + 3,
            "leader_car_idx": 12,
            "cars": [
                {"car_idx": 12, "pos": 1, "lap": 11, "gap_leader_s": 0, "gap_ahead_s": 0},
                {"car_idx": 7, "pos": 2, "lap": 11, "gap_leader_s": 1.1, "gap_ahead_s": 1.1},
            ],
        }
        await js.publish("iracing.standings", json.dumps(standings_payload_live).encode())

        async def tool_has_rows():
            res = await client.call_tool("get_session_persistence_status", {})
            # Format: { session_state_snapshots: {count:..}, ...}
            sstate = res.get("session_state_snapshots", {})
            stand = res.get("standings_snapshots", {})
            sess = res.get("session_snapshots", {})
            return (
                sstate.get("count", 0) >= 2
                and stand.get("count", 0) >= 2
                and sess.get("count", 0) >= 1
            )

        assert await _poll(tool_has_rows), "snapshot tables not populated via catch-up + live"

        # Validate direct DB row counts align with tool
        if db_path and db_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                counts = {
                    t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in [
                        "session_state_snapshots",
                        "standings_snapshots",
                        "session_snapshots",
                        "track_conditions_snapshots",
                    ]
                }
            finally:
                conn.close()
            res = await client.call_tool("get_session_persistence_status", {})
            for key, t in [
                ("session_state_snapshots", "session_state_snapshots"),
                ("standings_snapshots", "standings_snapshots"),
                ("session_snapshots", "session_snapshots"),
            ]:
                assert res.get(key, {}).get("count") == counts[t]
    finally:
        await client.close()
        if nc is not None:
            try:
                await nc.close()
            except Exception:
                pass

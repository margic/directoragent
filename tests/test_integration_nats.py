import os
import json
import sqlite3
import asyncio
import uuid
import time
import pytest
import pytest_asyncio

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
    """Ensure a JetStream stream exists; return True if present/created, False if unsupported."""
    try:
        try:
            # type: ignore[arg-type]
            await js.add_stream({"name": name, "subjects": subjects})
        except Exception:
            pass  # may already exist or lack perms
        # Verify
        try:
            info = await js.stream_info(name)
            if not info or not getattr(info.config, "name", None):
                return False
            return True
        except Exception:
            return False
    except Exception:
        return False


@pytest_asyncio.fixture
async def nats_setup():
    nc = await _try_connect_nats()
    _skip_if_no_nats(nc)
    js = nc.jetstream()  # type: ignore
    yield nc, js
    if nc is not None:
        try:
            await nc.drain()
        except Exception:
            pass


async def _start_client(env: dict[str, str]):
    # Apply environment for this run
    for k, v in env.items():
        os.environ[k] = v
    client = MCPToolClient()
    await client.start()
    return client


async def _poll(predicate, timeout=5.0, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if await predicate():
            return True
        await asyncio.sleep(interval)
    return False


@pytest.mark.integration
async def test_chat_jetstream_persistence_and_tools(nats_setup, tmp_path):
    nc, js = nats_setup
    # Derive effective settings (uses container env overrides if present)
    effective_settings = get_settings()
    chat_stream = effective_settings.chat_stream
    chat_subject = effective_settings.nats.chat_input_subject
    # Spec (docs/nats-messages.md): chat_stream should be YOUTUBE_CHAT, subject youtube.chat.message

    if not await _ensure_stream(js, chat_stream, [chat_subject]):
        pytest.skip("JetStream not available or insufficient permissions for chat stream")

    # Publish a chat message BEFORE starting the agent (tests catch-up path)
    msg_id_before = f"chat_{uuid.uuid4().hex[:8]}"
    chat_payload_before = {
        "type": "youtube_chat_message",
        "data": {
            "id": msg_id_before,
            "username": "Tester",
            "message": "Integration chat message (before)",
            "avatarUrl": "https://example.com/a.png",
            "timestamp": "2025-08-28T12:00:00.000Z",
            "type": "textMessageEvent",
        },
    }
    await js.publish(chat_subject, json.dumps(chat_payload_before).encode())

    db_path = tmp_path / "agent.db"
    env = {
        # Respect existing NATS_URL if already set; only set if missing
        **({} if os.environ.get("NATS_URL") else {"NATS_URL": NATS_URL}),
        **(
            {}
            if not os.environ.get("NATS_USERNAME")
            else {"NATS_USERNAME": os.environ.get("NATS_USERNAME")}
        ),
        **(
            {}
            if not os.environ.get("NATS_PASSWORD")
            else {"NATS_PASSWORD": os.environ.get("NATS_PASSWORD")}
        ),
        "SQLITE_PATH": str(db_path),
        "ENABLE_INGEST": "1",
        "DEFER_INGEST_INIT": "0",
        "ENABLE_CHAT": "1",
        "ENABLE_CHAT_PERSIST": "1",
        "ENABLE_JETSTREAM_CATCHUP": "1",
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
    }

    client = await _start_client(env)
    try:
        # Publish a second message AFTER start (live path)
        msg_id_after = f"chat_{uuid.uuid4().hex[:8]}"
        chat_payload_after = {
            "type": "youtube_chat_message",
            "data": {
                "id": msg_id_after,
                "username": "Tester",
                "message": "Integration chat message (after)",
                "avatarUrl": "https://example.com/a2.png",
                "timestamp": "2025-08-28T12:05:00.000Z",
                "type": "textMessageEvent",
            },
        }
        await js.publish(chat_subject, json.dumps(chat_payload_after).encode())

        target_ids = {msg_id_before, msg_id_after}

        # First poll sqlite directly to confirm persistence loop working
        async def in_sqlite():
            if not db_path.exists():
                return False
            try:
                conn = sqlite3.connect(db_path)
                try:
                    rows = conn.execute(
                        "SELECT id FROM chat_messages WHERE id IN (?,?)",
                        (msg_id_before, msg_id_after),
                    ).fetchall()
                    return any(r[0] in target_ids for r in rows)
                finally:
                    conn.close()
            except Exception:
                return False

        await _poll(in_sqlite, timeout=10.0)

        # Poll for either chat message to appear in recent tool
        async def has_chat_tool():
            res = await client.call_tool("get_recent_chat_messages", {"limit": 20})
            items = res.get("messages") or res.get("data") or res.get("items") or []
            # Implementation returns metadata; standard tool returns {messages: [...]}
            if isinstance(res, dict):
                # find any list in dict containing dicts with id
                for v in res.values():
                    if isinstance(v, list) and any(isinstance(x, dict) for x in v):
                        items = v
                        break
            return any(
                (m.get("data", {}).get("id") in target_ids) or (m.get("id") in target_ids)
                for m in items
            )

        assert await _poll(has_chat_tool, timeout=10.0), "Chat messages not surfaced via tool"

        # Check persisted in sqlite
        assert db_path.exists(), "sqlite file not created"
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT id, username, message FROM chat_messages WHERE id IN (?,?)",
                (msg_id_before, msg_id_after),
            ).fetchall()
            found_ids = {r[0] for r in rows}
            assert target_ids & found_ids, "Persisted rows missing expected chat IDs"
        finally:
            conn.close()

        # Full-text search should also find it (if FTS trigger created)
        res_search = await client.call_tool("search_chat", {"query": "Integration"})
        if isinstance(res_search, dict):
            hits = res_search.get("results", [])
            assert any(
                h.get("id") in target_ids for h in hits
            ), "search_chat did not return messages"
    finally:
        await client.close()


@pytest.mark.integration
async def test_iracing_incident_catchup_updates_snapshot(nats_setup):
    nc, js = nats_setup
    incident_stream = "IRACING_EVENTS"
    incident_subject = "iracing.incident"

    if not await _ensure_stream(js, incident_stream, [incident_subject]):
        pytest.skip("JetStream not available or insufficient permissions for incident stream")

    # Publish an incident BEFORE agent start to exercise catch-up
    incident_payload = {
        "timestamp": 1735123465.55,
        "car_idx": 42,
        "delta": 4,
        "total": 4,
        "team_total": 4,
    }
    await js.publish(incident_subject, json.dumps(incident_payload).encode())

    env = {
        **({} if os.environ.get("NATS_URL") else {"NATS_URL": NATS_URL}),
        "ENABLE_INGEST": "1",
        "DEFER_INGEST_INIT": "0",
        "ENABLE_INCIDENT_EVENTS": "1",
        "ENABLE_JETSTREAM_CATCHUP": "1",
    }
    client = await _start_client(env)
    try:

        async def snapshot_has_incident():
            snap = await client.call_tool("get_live_snapshot", {})
            inc = snap.get("incidents_recent") or []
            return any(e.get("car_idx") == 42 and e.get("total") == 4 for e in inc)

        assert await _poll(
            snapshot_has_incident
        ), "Incident not present in live snapshot after catch-up"
    finally:
        await client.close()

import os
import sqlite3
import time
from pathlib import Path

from sim_racecenter_agent.mcp.tools.search_corpus import build_search_corpus_tool

DB_PATH = "data/test_corpus.db"


def setup_module(module):
    os.environ["SQLITE_PATH"] = DB_PATH
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
    CREATE TABLE documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT,
        session_id TEXT,
        chunk_idx INT,
        text TEXT,
        hash TEXT,
        updated_at REAL
    );
    CREATE VIRTUAL TABLE documents_fts USING fts5(text, content='documents', content_rowid='rowid');
    CREATE TRIGGER documents_ai AFTER INSERT ON documents BEGIN
        INSERT INTO documents_fts(rowid, text) VALUES (new.rowid, new.text);
    END;
    CREATE TABLE chat_messages(
        id TEXT PRIMARY KEY,
        username TEXT,
        message TEXT,
        avatar_url TEXT,
        yt_type TEXT,
        ts_iso TEXT,
        ts REAL,
        day TEXT
    );
    CREATE VIRTUAL TABLE chat_messages_fts USING fts5(message, username, content='chat_messages', content_rowid='rowid');
    CREATE TRIGGER chat_messages_ai AFTER INSERT ON chat_messages BEGIN
        INSERT INTO chat_messages_fts(rowid, message, username) VALUES (new.rowid, new.message, new.username);
    END;
    """
    )
    now = time.time()
    conn.execute(
        "INSERT INTO documents(doc_type, session_id, chunk_idx, text, hash, updated_at) VALUES (?,?,?,?,?,?)",
        (
            "sporting_code",
            None,
            0,
            "Blue flag must be shown to a slower car being lapped.",
            "h1",
            now,
        ),
    )
    conn.execute(
        "INSERT INTO chat_messages(id, username, message, avatar_url, yt_type, ts_iso, ts, day) VALUES (?,?,?,?,?,?,?,?)",
        (
            "c1",
            "UserA",
            "Great blue flag enforcement today",
            "",
            "text",
            "2025-08-24T12:00:00Z",
            now,
            "2025-08-24",
        ),
    )
    conn.commit()
    conn.close()


def teardown_module(module):
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass


def test_search_corpus_both_scopes():
    tool = build_search_corpus_tool()
    out = tool["handler"]({"query": "blue flag", "limit": 5})
    assert out["hit_counts"]["rules"] == 1
    assert out["hit_counts"]["chat"] == 1
    assert len(out["results"]) == 2
    sources = {r["source"] for r in out["results"]}
    assert sources == {"rules", "chat"}


def test_search_corpus_scopes_filter():
    tool = build_search_corpus_tool()
    out = tool["handler"]({"query": "blue flag", "scopes": ["rules"]})
    assert set(out["hit_counts"].keys()) == {"rules"}
    assert all(r["source"] == "rules" for r in out["results"])


def test_search_corpus_empty_query():
    tool = build_search_corpus_tool()
    out = tool["handler"]({"query": "   "})
    assert out["errors"]["global"] == "empty_query"
    assert out["results"] == []

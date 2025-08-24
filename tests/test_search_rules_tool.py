import os
import sqlite3
import time
from pathlib import Path

from sim_racecenter_agent.mcp.tools.search_rules import build_search_rules_tool

DB_PATH = "data/test_rules.db"


def setup_module(module):
    os.environ["SQLITE_PATH"] = DB_PATH
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT,
            session_id TEXT,
            chunk_idx INT,
            text TEXT,
            hash TEXT,
            updated_at REAL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            text, content='documents', content_rowid='rowid'
        );
        CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts(rowid, text) VALUES (new.rowid, new.text);
        END;
        """
    )
    now = time.time()
    conn.execute(
        "INSERT INTO documents(doc_type, session_id, chunk_idx, text, hash, updated_at) VALUES (?,?,?,?,?,?)",
        ("sporting_code", None, 0, "Overtaking rules: A driver must leave space.", "hash1", now),
    )
    conn.execute(
        "INSERT INTO documents(doc_type, session_id, chunk_idx, text, hash, updated_at) VALUES (?,?,?,?,?,?)",
        ("sporting_code", None, 1, "Safety car procedure details.", "hash2", now),
    )
    conn.commit()
    conn.close()


def teardown_module(module):
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass


def test_search_rules_basic():
    tool = build_search_rules_tool()
    out = tool["handler"]({"query": "overtaking"})
    assert out["hit_count"] == 1
    assert (
        "Overtaking" in out["results"][0]["snippet"]
        or "overtaking" in out["results"][0]["snippet"].lower()
    )


def test_search_rules_empty_query():
    tool = build_search_rules_tool()
    out = tool["handler"]({"query": "  "})
    assert out["error"] == "empty query"
    assert out["hit_count"] == 0

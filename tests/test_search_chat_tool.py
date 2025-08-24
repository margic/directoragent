import os
import sqlite3
import time

from sim_racecenter_agent.mcp.tools.search_chat import build_search_chat_tool


def make_db(tmp_path):
    db = tmp_path / "chat.db"
    os.environ["SQLITE_PATH"] = str(db)
    conn = sqlite3.connect(db)
    conn.executescript(
        """
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
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    day = time.strftime("%Y-%m-%d", time.gmtime())
    conn.execute(
        "INSERT INTO chat_messages VALUES (?,?,?,?,?,?,?,?)",
        ("m1", "UserA", "Battle ahead!", "u.png", "text", "%s" % now, time.time(), day),
    )
    conn.execute(
        "INSERT INTO chat_messages VALUES (?,?,?,?,?,?,?,?)",
        ("m2", "UserB", "Nothing happening", "u.png", "text", "%s" % now, time.time(), day),
    )
    conn.commit()
    conn.close()


def test_search_chat_basic(tmp_path):
    make_db(tmp_path)
    tool = build_search_chat_tool()
    out = tool["handler"]({"query": "battle"})
    assert out["hit_count"] == 1
    assert out["results"][0]["id"] == "m1"


def test_search_chat_empty_query(tmp_path):
    make_db(tmp_path)
    tool = build_search_chat_tool()
    out = tool["handler"]({"query": "   "})
    assert out["hit_count"] == 0 and out.get("error") == "empty query"

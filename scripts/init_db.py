from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from sim_racecenter_agent.logging import get_logger

DB_PATH = os.environ.get("SQLITE_PATH", "data/agent.db")
_LOGGER = get_logger("init_db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

DDL = """
CREATE TABLE IF NOT EXISTS incidents_flat(
    id TEXT PRIMARY KEY,
    session_id TEXT,
    lap INT,
    cars TEXT,
    category TEXT,
    severity INT,
    ts REAL
);
CREATE TABLE IF NOT EXISTS documents(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type TEXT,
    session_id TEXT,
    chunk_idx INT,
    text TEXT,
    hash TEXT,
    updated_at REAL
);
CREATE TABLE IF NOT EXISTS embeddings(
    doc_id INT PRIMARY KEY,
    dim INT,
    vector BLOB,
    norm REAL
);
CREATE TABLE IF NOT EXISTS driver_stats(
    driver_id TEXT PRIMARY KEY,
    name TEXT,
    car_number INT,
    starts INT,
    wins INT,
    avg_finish REAL,
    incidents_per_hour REAL,
    updated_at REAL
);
CREATE TABLE IF NOT EXISTS summaries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    kind TEXT,
    content TEXT,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS answers_log(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT,
    question TEXT,
    answer TEXT,
    tools TEXT,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS faq_pairs(
    hash TEXT PRIMARY KEY,
    question TEXT,
    answer TEXT,
    last_used_at REAL,
    usage_count INT
);
-- Documents full text index (rules, manuals, etc.)
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    text, content='documents', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, text) VALUES (new.rowid, new.text);
END;
CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, text) VALUES('delete', old.rowid, old.text);
END;
CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, text) VALUES('delete', old.rowid, old.text);
    INSERT INTO documents_fts(rowid, text) VALUES (new.rowid, new.text);
END;
-- Chat messages raw store
CREATE TABLE IF NOT EXISTS chat_messages(
        id TEXT PRIMARY KEY,
        username TEXT,
        message TEXT,
        avatar_url TEXT,
        yt_type TEXT,
        ts_iso TEXT,
        ts REAL, -- epoch seconds
        day TEXT -- YYYY-MM-DD for partition style queries
);
-- Full text index (content + username)
CREATE VIRTUAL TABLE IF NOT EXISTS chat_messages_fts USING fts5(
        message, username, content='chat_messages', content_rowid='rowid'
);
-- Trigger to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS chat_messages_ai AFTER INSERT ON chat_messages BEGIN
    INSERT INTO chat_messages_fts(rowid, message, username) VALUES (new.rowid, new.message, new.username);
END;
CREATE TRIGGER IF NOT EXISTS chat_messages_ad AFTER DELETE ON chat_messages BEGIN
    INSERT INTO chat_messages_fts(chat_messages_fts, rowid, message, username) VALUES('delete', old.rowid, old.message, old.username);
END;
CREATE TRIGGER IF NOT EXISTS chat_messages_au AFTER UPDATE ON chat_messages BEGIN
    INSERT INTO chat_messages_fts(chat_messages_fts, rowid, message, username) VALUES('delete', old.rowid, old.message, old.username);
    INSERT INTO chat_messages_fts(rowid, message, username) VALUES (new.rowid, new.message, new.username);
END;
-- Session-related persistence
CREATE TABLE IF NOT EXISTS session_state_snapshots(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    data TEXT
);
CREATE TABLE IF NOT EXISTS session_snapshots(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    data TEXT
);
CREATE TABLE IF NOT EXISTS track_conditions_snapshots(
    ts REAL PRIMARY KEY,
    data TEXT
);
CREATE TABLE IF NOT EXISTS standings_snapshots(
    ts REAL,
    car_idx INT,
    position INT,
    car_number TEXT,
    driver TEXT,
    last_lap_s REAL,
    best_lap_s REAL,
    lap INT,
    created_at REAL,
    PRIMARY KEY(ts, car_idx)
);
CREATE INDEX IF NOT EXISTS idx_standings_snapshots_position ON standings_snapshots(position);
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(DDL)
        conn.commit()
        _LOGGER.info("Initialized DB at %s", DB_PATH)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

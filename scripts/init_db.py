from __future__ import annotations
import sqlite3
from pathlib import Path
import os

DB_PATH = os.environ.get("SQLITE_PATH", "data/agent.db")
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
"""

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(DDL)
        conn.commit()
        print(f"Initialized DB at {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
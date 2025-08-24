from __future__ import annotations

import os
import sqlite3
import time
from typing import Any

DB_PATH_ENV = "SQLITE_PATH"
DEFAULT_DB = "data/agent.db"


def _open_conn():
    path = os.environ.get(DB_PATH_ENV, DEFAULT_DB)
    # read-only URI if possible
    if not os.path.exists(path):
        return None
    return sqlite3.connect(path)


def build_search_chat_tool():
    """Tool definition for searching chat messages via FTS5.

    Input:
      query (str, required)
      limit (int, optional, default 10, 1..100)
      username (str, optional exact match filter)
      day (str, optional YYYY-MM-DD)
    Output:
      schema_version, generated_at, query, limit, hit_count, results[]
    """

    def handler(args: dict) -> dict:
        q = (args.get("query") or "").strip()
        if not q:
            return {
                "schema_version": 1,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "query": q,
                "limit": 0,
                "hit_count": 0,
                "results": [],
                "error": "empty query",
            }
        limit = int(args.get("limit", 10))
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100
        username = args.get("username")
        day = args.get("day")
        conn = _open_conn()
        if conn is None:
            return {
                "schema_version": 1,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "query": q,
                "limit": limit,
                "hit_count": 0,
                "results": [],
                "error": "database_missing",
            }
        try:
            # Check if FTS table exists
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages_fts'"
            )
            if not cur.fetchone():
                return {
                    "schema_version": 1,
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "query": q,
                    "limit": limit,
                    "hit_count": 0,
                    "results": [],
                    "error": "fts_missing",
                }
            base = (
                "SELECT cm.id, cm.username, cm.message, cm.ts_iso, cm.ts, bm25(chat_messages_fts) as score "
                "FROM chat_messages_fts JOIN chat_messages cm ON chat_messages_fts.rowid = cm.rowid "
                "WHERE chat_messages_fts MATCH ?"
            )
            params: list[Any] = [q]
            if username:
                base += " AND cm.username = ?"
                params.append(username)
            if day:
                base += " AND cm.day = ?"
                params.append(day)
            base += " ORDER BY score LIMIT ?"
            params.append(limit)
            rows = conn.execute(base, params).fetchall()
            results = [
                {
                    "id": r[0],
                    "username": r[1],
                    "message": r[2],
                    "timestamp": r[3],
                    "epoch": r[4],
                    "score": r[5],
                }
                for r in rows
            ]
            return {
                "schema_version": 1,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "query": q,
                "limit": limit,
                "hit_count": len(results),
                "results": results,
            }
        finally:
            conn.close()

    return {
        "name": "search_chat",
        "description": "Full-text search over ingested chat messages (FTS).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                "username": {"type": "string"},
                "day": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
            },
            "required": ["query"],
        },
        "output_schema": {"type": "object"},
        "handler": handler,
    }

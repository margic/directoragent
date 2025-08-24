from __future__ import annotations

import os
import sqlite3
import time

DB_PATH_ENV = "SQLITE_PATH"
DEFAULT_DB = "data/agent.db"


def _open_conn():
    path = os.environ.get(DB_PATH_ENV, DEFAULT_DB)
    if not os.path.exists(path):
        return None
    return sqlite3.connect(path)


def build_search_rules_tool():
    """Full-text search over ingested rule / sporting code documents.

    Input:
      query (str, required)
      limit (int, default 5, 1..50)
      doc_type (str, optional, defaults to 'sporting_code')
    Output: schema_version, generated_at, query, limit, hit_count, results[]
    Where results: [{doc_id, chunk_idx, score, snippet}]
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
        limit = int(args.get("limit", 5))
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50
        doc_type = args.get("doc_type", "sporting_code")
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
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'"
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
            sql = (
                "SELECT d.id, d.chunk_idx, bm25(documents_fts) as score, substr(d.text, max(1, instr(lower(d.text), lower(?)) - 60), 160) "
                "FROM documents_fts JOIN documents d ON documents_fts.rowid = d.rowid "
                "WHERE documents_fts MATCH ? AND d.doc_type = ? "
                "ORDER BY score LIMIT ?"
            )
            rows = conn.execute(sql, (q, q, doc_type, limit)).fetchall()
            results = [
                {
                    "doc_id": r[0],
                    "chunk_idx": r[1],
                    "score": r[2],
                    "snippet": r[3],
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
        "name": "search_rules",
        "description": "Full-text search over sporting code / rules documents (FTS).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                "doc_type": {"type": "string"},
            },
            "required": ["query"],
        },
        "output_schema": {"type": "object"},
        "handler": handler,
    }

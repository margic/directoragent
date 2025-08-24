from __future__ import annotations

import os
import sqlite3
import time
from typing import Any, Dict, List

DB_PATH_ENV = "SQLITE_PATH"
DEFAULT_DB = "data/agent.db"


def _open_conn():
    path = os.environ.get(DB_PATH_ENV, DEFAULT_DB)
    if not os.path.exists(path):
        return None
    return sqlite3.connect(path)


def _search_rules(
    conn: sqlite3.Connection, q: str, limit: int
) -> tuple[List[Dict[str, Any]], int, str | None]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'")
    if not cur.fetchone():
        return [], 0, "fts_missing"
    sql = (
        "SELECT d.id, d.chunk_idx, bm25(documents_fts) as score, substr(d.text, max(1, instr(lower(d.text), lower(?)) - 60), 180) "
        "FROM documents_fts JOIN documents d ON documents_fts.rowid = d.rowid "
        "WHERE documents_fts MATCH ? AND d.doc_type = 'sporting_code' ORDER BY score LIMIT ?"
    )
    rows = conn.execute(sql, (q, q, limit)).fetchall()
    results = [
        {
            "source": "rules",
            "id": r[0],
            "chunk_idx": r[1],
            "score": r[2],
            "snippet": r[3],
        }
        for r in rows
    ]
    return results, len(results), None


def _search_chat(
    conn: sqlite3.Connection, q: str, limit: int
) -> tuple[List[Dict[str, Any]], int, str | None]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages_fts'"
    )
    if not cur.fetchone():
        return [], 0, "fts_missing"
    sql = (
        "SELECT cm.id, cm.username, cm.message, cm.ts_iso, bm25(chat_messages_fts) as score "
        "FROM chat_messages_fts JOIN chat_messages cm ON chat_messages_fts.rowid = cm.rowid "
        "WHERE chat_messages_fts MATCH ? ORDER BY score LIMIT ?"
    )
    rows = conn.execute(sql, (q, limit)).fetchall()
    results = [
        {
            "source": "chat",
            "id": r[0],
            "username": r[1],
            "snippet": r[2],  # full message
            "timestamp": r[3],
            "score": r[4],
        }
        for r in rows
    ]
    return results, len(results), None


def build_search_corpus_tool():
    """Unified multi-scope search across available corpora (rules, chat, future embeddings).

    Current scopes implemented (lexical FTS only):
      - rules : sporting code chunks (documents/documents_fts)
      - chat  : chat messages (chat_messages/chat_messages_fts)

    Input:
      query (str, required)
      scopes (array[str], optional) subset of {rules, chat}; default = all available
      limit (int, optional, default 10, 1..100) global cap (per-scope also capped by this)

    Output:
      schema_version, generated_at, query, scopes_resolved, limit,
      results[] (merged, sorted by score ascending because bm25 lower = better),
      hit_counts {scope: count}, errors {scope: error_code}
    """

    def handler(args: dict) -> dict:
        q = (args.get("query") or "").strip()
        if not q:
            return {
                "schema_version": 1,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "query": q,
                "scopes_resolved": [],
                "limit": 0,
                "results": [],
                "hit_counts": {},
                "errors": {"global": "empty_query"},
            }
        limit = int(args.get("limit", args.get("top_k", 10)))  # backward compat top_k
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100
        requested_scopes = args.get("scopes") or ["rules", "chat"]
        requested_scopes = [s for s in requested_scopes if s in {"rules", "chat"}]
        if not requested_scopes:
            requested_scopes = ["rules", "chat"]
        conn = _open_conn()
        if conn is None:
            return {
                "schema_version": 1,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "query": q,
                "scopes_resolved": requested_scopes,
                "limit": limit,
                "results": [],
                "hit_counts": {s: 0 for s in requested_scopes},
                "errors": {s: "database_missing" for s in requested_scopes},
            }
        try:
            per_scope_limit = limit  # simple approach: each scope up to global limit
            all_results: List[Dict[str, Any]] = []
            hit_counts: Dict[str, int] = {}
            errors: Dict[str, str] = {}
            for scope in requested_scopes:
                if scope == "rules":
                    res, cnt, err = _search_rules(conn, q, per_scope_limit)
                elif scope == "chat":
                    res, cnt, err = _search_chat(conn, q, per_scope_limit)
                else:  # unreachable due to filtering
                    continue
                if err:
                    errors[scope] = err
                hit_counts[scope] = cnt
                all_results.extend(res)
            # Sort by score ascending (bm25)
            all_results.sort(key=lambda r: r.get("score", 1e9))
            # Trim to global limit
            if len(all_results) > limit:
                all_results = all_results[:limit]
            return {
                "schema_version": 1,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "query": q,
                "scopes_resolved": requested_scopes,
                "limit": limit,
                "results": all_results,
                "hit_counts": hit_counts,
                "errors": errors,
            }
        finally:
            conn.close()

    return {
        "name": "search_corpus",
        "description": "Unified multi-scope lexical search (rules + chat). Future: semantic fusion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scopes": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                "top_k": {"type": "integer"},  # backward-compatible alias
            },
            "required": ["query"],
        },
        "output_schema": {"type": "object"},
        "handler": handler,
    }

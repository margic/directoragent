#!/usr/bin/env python3
"""Ingest the sporting code PDF into the documents table with chunking + FTS.

Usage:
  python scripts/ingest_sporting_code.py --path docs/20250610-official_sporting_code_dated_Jun_10_2025.pdf \
        --chunk-size 1200 --overlap 120 --doc-type sporting_code

Idempotent: computes hash of each chunk; if a (doc_type, chunk_idx) exists with same hash, skips update.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import time
from sim_racecenter_agent.logging import get_logger
from pathlib import Path

try:
    from pypdf import PdfReader  # light dependency
except ImportError:  # pragma: no cover
    raise SystemExit("Missing dependency pypdf. Install with: pip install pypdf")

DB_PATH = os.environ.get("SQLITE_PATH", "data/agent.db")
_LOGGER = get_logger("ingest_sporting_code")

WHITESPACE_RE = re.compile(r"\s+")


def clean_text(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = WHITESPACE_RE.sub(" ", s).strip()
    return s


def chunk_text(text: str, chunk_size: int, overlap: int):
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + chunk_size)
        chunk = text[start:end]
        yield chunk
        if end == length:
            break
        start = end - overlap
        if start < 0:
            start = 0


def upsert_chunk(
    conn: sqlite3.Connection, doc_type: str, session_id: str | None, idx: int, chunk: str
):
    h = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
    cur = conn.execute(
        "SELECT id, hash FROM documents WHERE doc_type=? AND session_id IS ? AND chunk_idx=?",
        (doc_type, session_id, idx),
    )
    row = cur.fetchone()
    now = time.time()
    if row:
        doc_id, existing_hash = row
        if existing_hash == h:
            return False, doc_id
        conn.execute(
            "UPDATE documents SET text=?, hash=?, updated_at=? WHERE id=?",
            (chunk, h, now, doc_id),
        )
        return True, doc_id
    else:
        cur = conn.execute(
            "INSERT INTO documents(doc_type, session_id, chunk_idx, text, hash, updated_at) VALUES (?,?,?,?,?,?)",
            (doc_type, session_id, idx, chunk, h, now),
        )
        return True, cur.lastrowid


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt:
            parts.append(clean_text(txt))
    return "\n".join(p for p in parts if p)


def ingest(path: Path, doc_type: str, chunk_size: int, overlap: int, session_id: str | None):
    if not path.exists():
        raise FileNotFoundError(path)
    raw = extract_pdf_text(path)
    if not raw.strip():
        raise RuntimeError("No text extracted from PDF")
    # Collapse excessive newlines for chunking; keep single newlines to hint paragraphs.
    raw = re.sub(r"\n{2,}", "\n", raw)
    conn = sqlite3.connect(DB_PATH)
    updated = 0
    try:
        for idx, chunk in enumerate(chunk_text(raw, chunk_size, overlap)):
            changed, _doc_id = upsert_chunk(conn, doc_type, session_id, idx, chunk)
            if changed:
                updated += 1
        conn.commit()
        _LOGGER.info("Ingestion complete. chunks=%s changed=%s", idx + 1, updated)
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--doc-type", default="sporting_code")
    ap.add_argument("--session-id", default=None)
    ap.add_argument("--chunk-size", type=int, default=1200)
    ap.add_argument("--overlap", type=int, default=120)
    args = ap.parse_args()
    ingest(Path(args.path), args.doc_type, args.chunk_size, args.overlap, args.session_id)


if __name__ == "__main__":
    main()

from __future__ import annotations
import time

def build_search_corpus_tool():
    # Placeholder – returns empty until embeddings implemented
    def handler(args: dict) -> dict:
        query = args.get("query", "")
        top_k = args.get("top_k", 5)
        return {
            "schema_version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query": query,
            "matches": [],
            "top_k": top_k,
            "index_version": 0
        }
    return {
        "name": "search_corpus",
        "description": "Semantic search across domain corpus (stub).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        },
        "output_schema": {"type": "object"},
        "handler": handler
    }
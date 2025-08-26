from __future__ import annotations
from typing import List, Dict, Any, Optional
import json
import os
import httpx
from ..config.settings import get_settings

"""Pattern B multi-step reasoning support.

Step 1: Ask LLM which tools (by name + args JSON) are needed for a user message.
Step 2: Execute tools.
Step 3: Provide tool JSON outputs + original message to LLM to craft final answer (<=200 chars).

If LLM proposes unknown tools or empty list -> return None (ignore).
"""

TOOL_CATALOG_FIELDS = ["name", "description", "input_schema"]


def build_tool_catalog(tools_meta: List[dict]) -> str:
    lines = []
    for t in tools_meta:
        name = t.get("name")
        desc = t.get("description")
        props = (t.get("input_schema") or {}).get("properties", {})
        lines.append(f"- {name}: {desc} args={list(props.keys())}")
    return "\n".join(lines)


async def _gemini_call(model: str, prompt: str, temperature: float = 0) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    endpoint = os.environ.get(
        "GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/"
    )
    if not api_key:
        return None
    url = f"{endpoint}{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None
    text = None
    for c in data.get("candidates", []) or []:
        parts = ((c.get("content") or {}).get("parts")) or []
        for p in parts:
            if p.get("text"):
                text = p["text"].strip()
                break
        if text:
            break
    if not text:
        return None
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.startswith("```")]
        text = "\n".join(lines).strip()
    return text


async def plan_tools(message: str, tools_meta: List[dict]) -> Optional[List[dict]]:
    catalog = build_tool_catalog(tools_meta)
    model = get_settings().llm_planner_model
    prompt = (
        "You are a planner for a sim racing director agent.\n"
        "Given the user chat message decide which tools to call and minimal arguments.\n"
        'Return pure JSON: {"plan":[{"name":<tool>,"arguments":{}}],"rationale":<short>}\n'
        'If no tool applies return {"plan":[],"rationale":<why>}\n'
        f"Tools:\n{catalog}\n"
        f"Message: {message}\nJSON:"
    )
    raw = await _gemini_call(model, prompt)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    plan = parsed.get("plan")
    if not isinstance(plan, list):
        return None
    # Basic validation
    allowed = {t.get("name") for t in tools_meta}
    cleaned: List[dict] = []
    for step in plan:
        if not isinstance(step, dict):
            continue
        nm = step.get("name")
        if nm not in allowed:
            continue
        args = step.get("arguments") if isinstance(step.get("arguments"), dict) else {}
        cleaned.append({"name": nm, "arguments": args})
    return cleaned


async def synthesize_answer(message: str, tool_results: Dict[str, Any]) -> Optional[str]:
    model = get_settings().llm_answer_model
    tool_json = json.dumps(tool_results, separators=(",", ":"))
    prompt = (
        "You are a race director assistant. Craft a concise answer (<=200 chars) to the user message\n"
        "using ONLY provided tool JSON. Do not invent data not present. If insufficient data, respond with a brief apology + unknown.\n"
        f"Message: {message}\n"
        f"Tools JSON: {tool_json}\n"
        'Return JSON only: {"answer":<text>}'
    )
    raw = await _gemini_call(model, prompt, temperature=0.2)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    ans = (parsed.get("answer") or "").strip()
    if not ans:
        return None
    return ans[:200]

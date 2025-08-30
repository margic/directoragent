from __future__ import annotations

import os
import sys
from typing import Any

from sim_racecenter_agent.mcp.client_wrapper import MCPToolClient
from sim_racecenter_agent.logging import get_logger

LOG = get_logger("gemini_direct")

try:  # lazy import; allow running tests without SDK present
    from google import genai  # type: ignore
    from google.genai import types as genai_types  # type: ignore
except Exception:  # pragma: no cover
    genai = None  # type: ignore
    genai_types = None  # type: ignore


class GeminiToolSession:
    """Expose MCP tools to Gemini with optional function-calling & configurable greeting.

    Environment variables:
      GEMINI_API_KEY            - required to contact Gemini
      DIRECTOR_SYSTEM_PROMPT    - prepended to user prompt (as system context)
      DIRECTOR_GREETING         - static greeting for simple hello (supports {tools} placeholder)
      GEMINI_DISABLE_CALLS=1    - disable function/tool calling loop
    """

    def __init__(self, model: str | None = None, server_cmd: str | None = None):
        self.model = model or os.environ.get("LLM_ANSWER_MODEL", "gemini-2.5-flash")
        self.client = MCPToolClient(server_cmd=server_cmd)
        self._gemini_client: Any | None = None
        self._started = False
        self._gemini_tools: list[Any] = []
        self._tool_names: list[str] = []
        self._system_prompt = os.environ.get("DIRECTOR_SYSTEM_PROMPT", "")
        self._greeting = os.environ.get("DIRECTOR_GREETING", "")

    async def ensure_started(self) -> int:
        if self._started:
            return len(self._gemini_tools)
        if genai is None:
            raise RuntimeError(
                "google-genai package not installed in interpreter "
                f"{sys.executable}. Install with 'pip install google-genai'."
            )
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY not set")
        await self.client.start()
        mcp_tools = await self.client.list_tools()
        LOG.info("GeminiToolSession tools=%d", len(mcp_tools))
        self._tool_names = [
            t.get("name")
            for t in mcp_tools
            if isinstance(t, dict) and isinstance(t.get("name"), str)
        ]
        self._gemini_client = genai.Client()
        self._gemini_tools = self._build_gemini_tools(mcp_tools)
        self._started = True
        return len(mcp_tools)

    def tool_names(self) -> list[str]:  # type: ignore[no-untyped-def]
        return list(self._tool_names)

    async def ask(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_chars: int = 400,
        enable_function_calls: bool | None = None,
        max_tool_rounds: int = 2,
    ) -> str:  # type: ignore[no-untyped-def]
        await self.ensure_started()
        assert self._gemini_client is not None
        if enable_function_calls is None:
            enable_function_calls = os.getenv("GEMINI_DISABLE_CALLS") != "1"
        # Greeting short circuit
        low = prompt.strip().lower()
        if self._greeting and low in {"hi", "hello", "hey", "hey there", "hello!"}:
            return self._expand_greeting()
        tools_decl = self._gemini_tools if enable_function_calls else []
        full_prompt = prompt
        if self._system_prompt:
            full_prompt = f"{self._system_prompt.strip()}\n\nUser: {prompt}".strip()
        cfg = genai_types.GenerateContentConfig(  # type: ignore[attr-defined]
            temperature=temperature,
            tools=tools_decl,
        )
        resp = await self._gemini_client.aio.models.generate_content(  # type: ignore[union-attr]
            model=self.model,
            contents=full_prompt,
            config=cfg,
        )
        if enable_function_calls:
            resp = await self._maybe_execute_function_calls(resp, cfg, prompt, max_tool_rounds)
        text = self._extract_text(resp)
        if enable_function_calls and not text:
            # Some responses may only contain function_call parts with no plain text; log for visibility.
            LOG.debug(
                "Gemini returned no textual parts after function call loop model=%s prompt=%r",
                self.model,
                prompt[:80],
            )
        if max_output_chars and len(text) > max_output_chars:
            text = text[: max_output_chars - 1] + "…"
        return text

    def _expand_greeting(self) -> str:  # type: ignore[no-untyped-def]
        g = self._greeting or ""
        if "{tools}" in g:
            g = g.replace("{tools}", ", ".join(self._tool_names))
        return g

    async def close(self):
        try:
            await self.client.close()
        except Exception:
            pass
        self._started = False

    # --- internal helpers ---
    def _build_gemini_tools(self, mcp_tools):  # type: ignore[no-untyped-def]
        if genai_types is None:
            return []
        decls = []
        for t in mcp_tools:
            if not isinstance(t, dict):
                continue
            name = t.get("name")
            if not name:
                continue
            desc = t.get("description") or name
            raw_schema = t.get("input_schema") if isinstance(t.get("input_schema"), dict) else {}
            params: dict = {"type": "object", "properties": {}}
            if isinstance(raw_schema, dict):
                props = raw_schema.get("properties")
                if isinstance(props, dict):
                    clean_props = {}
                    for pname, spec in props.items():
                        if pname == "context" or not isinstance(spec, dict):
                            continue
                        if any(k.startswith("$") for k in spec.keys()) or any(
                            "$ref" in str(v) for v in spec.values()
                        ):
                            continue
                        allowed = {
                            "type",
                            "description",
                            "enum",
                            "items",
                            "properties",
                            "required",
                            "minimum",
                            "maximum",
                            "default",
                        }
                        cleaned = {k: v for k, v in spec.items() if k in allowed}
                        if "type" not in cleaned:
                            cleaned["type"] = spec.get("type", "string")
                        clean_props[pname] = cleaned
                    params["properties"] = clean_props
                required_list = raw_schema.get("required")
                if isinstance(required_list, list):
                    req = [r for r in required_list if r in (params.get("properties") or {})]
                    if req:
                        params["required"] = req
            try:
                fn = genai_types.FunctionDeclaration(  # type: ignore[attr-defined]
                    name=name,
                    description=desc,
                    parameters=params,
                )
                decls.append(fn)
            except Exception:
                LOG.debug("Failed to build function declaration for %s", name, exc_info=True)
        if not decls:
            return []
        try:
            container = genai_types.Tool(function_declarations=decls)  # type: ignore[attr-defined]
            return [container]
        except Exception:
            LOG.debug("Failed to wrap function declarations", exc_info=True)
            return []

    async def _maybe_execute_function_calls(
        self, first_resp, base_cfg, original_prompt, max_rounds
    ):  # type: ignore[no-untyped-def]
        if genai_types is None:
            return first_resp
        calls = self._extract_function_calls(first_resp)
        rounds = 0
        accum_contents = [original_prompt]
        while calls and rounds < max_rounds:
            rounds += 1
            tool_outputs = []
            for fc in calls:
                name = (
                    getattr(fc, "name", None)
                    or getattr(fc, "function_name", None)
                    or (fc.get("name") if isinstance(fc, dict) else None)
                )
                args = (
                    getattr(fc, "args", None)
                    or getattr(fc, "arguments", None)
                    or (fc.get("args") if isinstance(fc, dict) else None)
                )
                if isinstance(args, str):
                    import json as _json

                    try:
                        args = _json.loads(args)
                    except Exception:
                        args = {}
                if not isinstance(args, dict):
                    args = {}
                if not name:
                    continue
                try:
                    tool_result = await self.client.call_tool(name, args)
                except Exception as e:  # pragma: no cover
                    tool_result = {"error": str(e)}
                tool_outputs.append({"name": name, "output": tool_result})
            if not tool_outputs:
                break
            accum_contents.append(f"TOOL_RESULTS_ROUND_{rounds}: {tool_outputs}")
            followup_prompt = "\n".join(accum_contents)
            second = await self._gemini_client.aio.models.generate_content(  # type: ignore[union-attr]
                model=self.model,
                contents=followup_prompt,
                config=base_cfg,
            )
            calls = self._extract_function_calls(second)
            first_resp = second
        return first_resp

    def _extract_function_calls(self, resp):  # type: ignore[no-untyped-def]
        """Return list of function call objects from response.

        Handles current SDK shapes: candidate.content.parts[*].function_call. Older code
        mistakenly iterated over candidate.content directly.
        """
        calls = []
        cand_list = getattr(resp, "candidates", []) or []
        for cand in cand_list:
            content = getattr(cand, "content", None)
            parts = []
            if content is not None:
                parts = getattr(content, "parts", []) or []
            if not parts:
                parts = getattr(cand, "parts", []) or []
            for part in parts:
                fc = getattr(part, "function_call", None) or getattr(part, "functionCall", None)
                if fc:
                    calls.append(fc)
        return calls

    def _extract_text(self, resp) -> str:  # type: ignore[no-untyped-def]
        """Best-effort extraction of textual content from a Gemini response object.

        Avoids TypeError caused by attempting to join non-string Candidate objects.
        """
        # Direct text aggregation if present
        direct = getattr(resp, "text", None)
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        pieces: list[str] = []
        for cand in getattr(resp, "candidates", []) or []:
            # candidate.content may itself have 'parts'
            content = getattr(cand, "content", None)
            parts = []
            if content is not None:
                parts = getattr(content, "parts", []) or []
            # Some SDK variants expose parts directly on candidate
            if not parts:
                parts = getattr(cand, "parts", []) or []
            for part in parts:
                t = getattr(part, "text", None)
                if isinstance(t, str) and t:
                    pieces.append(t)
        return "".join(pieces).strip()


__all__ = ["GeminiToolSession"]

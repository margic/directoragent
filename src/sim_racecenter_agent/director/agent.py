from __future__ import annotations
import os
from sim_racecenter_agent.logging import get_logger
from .gemini_direct import GeminiToolSession

LOG = get_logger("director_agent")


class DirectorAgent:
    """Simplified agent: delegates all reasoning to Gemini via MCP tool session."""

    def __init__(self, server_cmd: str | None = None):
        self._answer_lock = False
        self._gemini = GeminiToolSession(server_cmd=server_cmd or os.environ.get("MCP_SERVER_CMD"))

    async def answer(self, message: str) -> str | None:
        if self._answer_lock:
            LOG.debug("answer() overlap; dropping %r", message)
            return None
        self._answer_lock = True
        try:
            try:
                if not self._gemini._started:
                    LOG.info("[director_agent] starting Gemini tool session (lazy cold start)")
                    await self._gemini.ensure_started()
            except Exception as e:
                LOG.error("GeminiToolSession start failed: %s", e)
                return None
            try:
                answer = await self._gemini.ask(message)
            except Exception as e:
                LOG.error("Gemini generation failed: %s", e)
                return None
            return (answer or "").strip() or None
        finally:
            self._answer_lock = False

    async def close(self):
        try:
            await self._gemini.close()
        except Exception:
            pass
        finally:
            self._answer_lock = False

    async def prewarm(self) -> int:
        """Eagerly start Gemini + MCP and return number of tools.

        Used by ChatResponder background prewarm task. Safe to call multiple times.
        """
        try:
            return await self._gemini.ensure_started()
        except Exception as e:  # pragma: no cover - best effort
            LOG.warning("prewarm failed: %s", e)
            return 0

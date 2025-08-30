"""FastMCP stdio client wrapper used by the DirectorAgent when MCP_MODE=stdio.

Spawns the MCP server process (python -m sim_racecenter_agent.mcp.sdk_server) and
exposes list_tools / call_tool methods returning shapes compatible with existing
reasoning pipeline (snake_case input_schema key).
"""

from __future__ import annotations

import asyncio
import os
import json
from typing import Any, List, Dict, Optional

from sim_racecenter_agent.logging import get_logger

LOG = get_logger("mcp_stdio_client")


class MCPToolClient:
    def __init__(self, server_cmd: Optional[str] = None):
        if not server_cmd:
            server_cmd = "python -u -m sim_racecenter_agent.mcp.sdk_server"
        self._cmd_parts = server_cmd.strip().split()
        forward_keys = [
            *[k for k in os.environ.keys() if k.startswith("NATS_")],
            *[k for k in os.environ.keys() if k.startswith("ENABLE_")],
            # Legacy flag forwarded only if present for backward compat
            "DISABLE_INGEST",
            "TEST_ENABLE_MUTATE",
            "LOG_LEVEL",
            "SQLITE_PATH",
            "DEFER_INGEST_INIT",
            "DEFER_INGEST_DELAY",
        ]
        self._env_subset = {k: os.environ[k] for k in forward_keys if k in os.environ}
        LOG.debug("[mcp_client] prepared server env_keys=%s", sorted(self._env_subset.keys()))
        # Runtime state
        self._proc: asyncio.subprocess.Process | None = None
        self._stdout: asyncio.StreamReader | None = None
        self._stdin: asyncio.StreamWriter | None = None
        self._stderr: asyncio.StreamReader | None = None
        self._started = False
        self._lock = asyncio.Lock()
        self._id = 0
        # Backcompat sentinel
        self._session = True

    async def start(self):
        if self._started:
            return
        async with self._lock:
            if self._started:
                return
            import time as _t

            t0 = _t.time()
            LOG.info("[mcp_client] spawning server cmd=%s", " ".join(self._cmd_parts))
            try:
                self._proc = await asyncio.create_subprocess_exec(
                    self._cmd_parts[0],
                    *self._cmd_parts[1:],
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, **self._env_subset},
                )
                assert self._proc.stdin and self._proc.stdout
                self._stdin = self._proc.stdin
                self._stdout = self._proc.stdout
                self._stderr = self._proc.stderr  # type: ignore[assignment]
                t_spawn = _t.time()
                # Initialize
                init_params = {
                    "protocolVersion": os.environ.get("MCP_PROTOCOL_VERSION", "2024-07-01"),
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "director-agent", "version": "0.1.0"},
                }
                init_req = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": init_params,
                }
                await self._write(json.dumps(init_req))
                resp = await self._read_until_id(
                    1, timeout=float(os.environ.get("MCP_INIT_RESP_TIMEOUT", "5"))
                )
                if not resp or resp.get("error"):
                    raise RuntimeError(f"initialize failed: {resp}")
                t_init = _t.time()
                # Send notifications/initialized
                try:
                    await self._write(
                        json.dumps(
                            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
                        )
                    )
                except Exception:  # pragma: no cover
                    LOG.debug("[mcp_client] failed sending initialized notification", exc_info=True)
                self._started = True
                LOG.info(
                    "[mcp_client] started spawn=%.2fs init=%.2fs total=%.2fs",
                    t_spawn - t0,
                    t_init - t_spawn,
                    t_init - t0,
                )
            except Exception:
                LOG.error("[mcp_client] start failed", exc_info=True)
                await self.close()
                raise

    async def close(self):
        if not self._started and not self._proc:
            return
        proc = self._proc
        stdin = self._stdin
        stdout = self._stdout
        stderr = self._stderr
        self._started = False
        # Attempt graceful shutdown: send shutdown -> exit, then close stdin (EOF)
        try:
            if proc and proc.returncode is None and stdin:
                try:
                    # Send shutdown request (ignore errors/timeouts)
                    sid = self._next_id()
                    shutdown_req = {
                        "jsonrpc": "2.0",
                        "id": sid,
                        "method": "shutdown",
                        "params": {},
                    }
                    await self._write(json.dumps(shutdown_req))
                    # Wait briefly for response
                    try:
                        await asyncio.wait_for(self._read_until_id(sid), timeout=1.5)
                    except Exception:  # pragma: no cover
                        pass
                    # Send exit notification
                    try:
                        await self._write(json.dumps({"jsonrpc": "2.0", "method": "exit"}))
                    except Exception:  # pragma: no cover
                        pass
                except Exception:  # pragma: no cover
                    LOG.debug("[mcp_client] graceful shutdown RPC phase failed", exc_info=True)
                # Close stdin to send EOF
                try:
                    stdin.close()
                except Exception:  # pragma: no cover
                    pass

            # Drain remaining stdout/stderr concurrently with wait
            async def _drain(reader: asyncio.StreamReader | None, label: str):
                if not reader:
                    return
                try:
                    # Read a limited number of lines to avoid infinite loop if stream stalls
                    for _ in range(200):
                        if proc and proc.returncode is not None:
                            break
                        line = await asyncio.wait_for(reader.readline(), timeout=0.25)
                        if not line:
                            break
                except Exception:
                    pass

            wait_timeout = float(os.environ.get("MCP_SHUTDOWN_TIMEOUT", "5"))
            if proc and proc.returncode is None:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(
                            _drain(stdout, "stdout"), _drain(stderr, "stderr"), proc.wait()
                        ),
                        timeout=wait_timeout,
                    )
                except asyncio.TimeoutError:  # pragma: no cover
                    # escalate to terminate then kill
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=1.5)
                    except asyncio.TimeoutError:
                        try:
                            proc.kill()
                        except Exception:
                            pass
        except Exception as e:  # pragma: no cover
            LOG.debug("[mcp_client] close error: %s", e)
        finally:
            self._proc = None
            self._stdout = None
            self._stderr = None
            self._stdin = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        assert self._started and self._stdin and self._stdout, "MCP session not started"
        req_id = self._next_id()
        await self._write(
            json.dumps({"jsonrpc": "2.0", "id": req_id, "method": "tools/list", "params": {}})
        )
        resp = await self._read_until_id(req_id)
        if not resp or resp.get("error"):
            raise RuntimeError(f"tools/list failed: {resp}")
        tools = resp.get("result", {}).get("tools", [])
        out: List[Dict[str, Any]] = []
        for t in tools:
            out.append(
                {
                    "name": t.get("name"),
                    "description": t.get("description") or t.get("name"),
                    "input_schema": t.get("inputSchema"),
                }
            )
        return out

    async def call_tool(self, name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        assert self._started and self._stdin and self._stdout, "MCP session not started"
        req_id = self._next_id()
        await self._write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}},
                }
            )
        )
        resp = await self._read_until_id(req_id)
        if not resp:
            raise RuntimeError("No response for tools/call")
        if resp.get("error"):
            raise RuntimeError(f"Tool {name} error: {resp['error']}")
        content = resp.get("result", {}).get("content")
        if isinstance(content, list) and content and isinstance(content[0], dict):
            first = content[0]
            if first.get("type") == "json":
                return first.get("value") or {}
            if first.get("type") == "text" and isinstance(first.get("text"), str):
                txt = first.get("text")
                # Attempt JSON decode for convenience
                import json as _json

                try:
                    return _json.loads(txt)
                except Exception:
                    return {"text": txt}
        return resp.get("result", {})

    async def warm(self) -> int:
        """Ensure server started and return number of tools available (for prewarming)."""
        await self.start()
        tools = await self.list_tools()
        LOG.info("[mcp_client] warm complete tools=%d", len(tools))
        return len(tools)

    # --- internal helpers ---
    def _next_id(self) -> int:
        self._id += 1
        return self._id + 100  # avoid colliding with manual init id=1

    async def _write(self, line: str):
        assert self._stdin is not None
        self._stdin.write((line + "\n").encode())
        await self._stdin.drain()

    async def _read_until_id(self, rid: int, timeout: float | None = None):
        assert self._stdout is not None
        end = None if timeout is None else (asyncio.get_event_loop().time() + timeout)
        while True:
            if end is not None and asyncio.get_event_loop().time() > end:
                raise asyncio.TimeoutError(f"Timeout waiting for id={rid}")
            raw = await self._stdout.readline()
            if not raw:
                return None
            try:
                obj = json.loads(raw.decode())
            except Exception:
                continue
            if obj.get("id") == rid:
                return obj


__all__ = ["MCPToolClient"]

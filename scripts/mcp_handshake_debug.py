#!/usr/bin/env python
"""Direct handshake debug for FastMCP sdk_server.

Spawns: python -u -m sim_racecenter_agent.mcp.sdk_server
Writes a single JSON-RPC initialize line, waits for response, then list_tools.
Prints raw lines read with timestamps for diagnosing handshake stalls.
"""

from __future__ import annotations
import asyncio
import json
import os
import time
import shlex

SERVER_CMD = os.environ.get("MCP_SERVER_CMD", "python -u -m sim_racecenter_agent.mcp.sdk_server")
PARTS = shlex.split(SERVER_CMD)

INIT_REQ = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-07-01",
        "capabilities": {"tools": {}},
        "clientInfo": {"name": "debug-handshake", "version": "0.0.1"},
    },
}
LIST_REQ = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
INITIALIZED_NOTE = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}


async def main():
    env_forward = {
        k: v
        for k, v in os.environ.items()
        if k.startswith("NATS_")
        or k.startswith("ENABLE_")
        # legacy DISABLE_INGEST forwarded
        or k in {"LOG_LEVEL", "DISABLE_INGEST", "DEFER_INGEST_INIT"}
    }
    print(f"[handshake] spawning: {' '.join(PARTS)} env_keys={sorted(env_forward.keys())}")
    proc = await asyncio.create_subprocess_exec(
        PARTS[0],
        *PARTS[1:],
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **env_forward},
    )
    assert proc.stdout is not None and proc.stdin is not None and proc.stderr is not None
    t0 = time.time()
    # send initialize only first
    proc.stdin.write(json.dumps(INIT_REQ).encode() + b"\n")
    await proc.stdin.drain()

    lines = []

    async def reader():
        while True:
            # proc.stdout asserted non-None above
            line = await proc.stdout.readline()  # type: ignore[union-attr]
            if not line:
                break
            ts = time.time() - t0
            text = line.decode().rstrip()[:500]
            print(f"[stdout+{ts:0.3f}s] {text}")
            lines.append(text)
            if '"id": 1' in text or '"id":1' in text:
                # type: ignore[union-attr]
                proc.stdin.write(json.dumps(INITIALIZED_NOTE).encode() + b"\n")
                await proc.stdin.drain()  # type: ignore[union-attr]
                await asyncio.sleep(0.05)
                # type: ignore[union-attr]
                proc.stdin.write(json.dumps(LIST_REQ).encode() + b"\n")
                await proc.stdin.drain()  # type: ignore[union-attr]
            if '"id": 2' in text or '"id":2' in text:
                try:
                    proc.terminate()
                except Exception:
                    pass
                break

    async def err_reader():
        while True:
            line = await proc.stderr.readline()  # type: ignore[union-attr]
            if not line:
                break
            ts = time.time() - t0
            print(f"[stderr+{ts:0.3f}s] {line.decode().rstrip()[:500]}")

    await asyncio.wait_for(asyncio.gather(reader(), err_reader()), timeout=10)
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    print(f"[handshake] exit={proc.returncode} lines={len(lines)}")


if __name__ == "__main__":
    asyncio.run(main())

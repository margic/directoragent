from __future__ import annotations

from sim_racecenter_agent.mcp import sdk_server

"""Compatibility wrapper to launch the FastMCP stdio server.

Legacy logic combined HTTP + cache bootstrap. That server has been removed.
Use this script if external tooling expects a runnable file instead of -m.
"""

if __name__ == "__main__":  # pragma: no cover
    sdk_server.run_stdio()

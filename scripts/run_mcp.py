from __future__ import annotations
import asyncio
from sim_racecenter_agent.mcp.server import bootstrap

if __name__ == "__main__":
    asyncio.run(bootstrap())
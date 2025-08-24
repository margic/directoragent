from __future__ import annotations

import asyncio

import click

from ..director.agent import DirectorAgent


@click.group()
def cli():
    """Sim RaceCenter Agent CLI"""


@cli.command()
@click.argument("message", type=str)
@click.option("--mcp", default="http://localhost:8000", help="MCP base URL")
def ask(message: str, mcp: str):
    """Send a test message to DirectorAgent."""

    async def _run():
        agent = DirectorAgent(mcp)
        ans = await agent.answer(message)
        click.echo(ans or "(No answer)")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()

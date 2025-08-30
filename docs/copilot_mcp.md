### Copilot MCP Integration

The dev container pre-configures GitHub Copilot Chat to launch the Sim RaceCenter MCP stdio server.

Server config key: `racecenter`.

What was added (see `.devcontainer/devcontainer.json`):
```
"github.copilot.chat.modelContextProtocol.enabled": true,
"github.copilot.chat.modelContextProtocol.serverConfigurations": {
  "racecenter": {
    "command": "python",
    "args": ["-m", "sim_racecenter_agent.mcp.sdk_server"],
    "cwd": "/workspaces/directoragent",
    "env": { ... }
  }
}
```

Usage:
1. Rebuild / reopen the container (ensures dependencies installed).
2. Open Copilot Chat.
3. Ask a question, optionally hint provider name (e.g. *"Who is leading? racecenter"*). Copilot should call `tools/list` then `tools/call`.

Tools exposed: `get_live_snapshot`, `get_current_battle`, `get_fastest_practice`, `search_corpus`, `search_chat`, `get_roster`.

Environment inheritance: `NATS_URL` and feature flags are passed through so telemetry populates the cache.

If you add new tools: add a new build_* function and append to `_existing_builders` in `sdk_server.py`, then rebuild the container or reload the window.

Troubleshooting:
* No tools listed: verify Copilot extension version supports MCP and that setting `...modelContextProtocol.enabled` is true. Also confirm the server process started (check "Ports" or run manually below).
* Empty data: ensure NATS reachable (`NATS_URL`) and feature flags set (already in config). Check logs by running the server manually: `python -m sim_racecenter_agent.mcp.sdk_server` and sending a `tools/list` JSON-RPC line with an MCP client.

Manual stdio test (raw JSON-RPC via module):
```
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m sim_racecenter_agent.mcp.sdk_server
```

Add provider to a single workspace only: you can copy those two settings into `.vscode/settings.json` if you prefer per-workspace override.

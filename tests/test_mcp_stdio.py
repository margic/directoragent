import json
import sys
import subprocess
import pathlib


def test_mcp_stdio_list_and_battle_empty():
    script = pathlib.Path("scripts/mcp_stdio.py")
    assert script.exists(), "mcp_stdio.py script missing"
    # Two JSON-RPC requests: list_tools then call_tool for get_current_battle with no data
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "list_tools"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "call_tool",
            "params": {"name": "get_current_battle", "arguments": {}},
        },
    ]
    input_payload = "\n".join(json.dumps(r) for r in reqs) + "\n"
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate(input_payload, timeout=10)
    assert proc.returncode == 0, f"Non-zero exit {proc.returncode}, stderr: {err}"
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) >= 2, f"Expected at least 2 response lines, got {lines} / stderr: {err}"
    resp1 = json.loads(lines[0])
    resp2 = json.loads(lines[1])
    # Validate list_tools
    assert resp1.get("id") == 1 and "result" in resp1, f"Bad list_tools response: {resp1}"
    tools = resp1["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "get_current_battle" in names, f"Tool not registered; tools = {names}"
    # Validate call_tool
    assert resp2.get("id") == 2 and "result" in resp2, f"Bad call_tool response: {resp2}"
    result = resp2["result"]
    assert "pairs" in result and isinstance(result["pairs"], list)
    assert result.get("roster_size") == 0

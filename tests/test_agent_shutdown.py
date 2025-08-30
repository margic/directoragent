import os
import subprocess
import sys
import time


def test_agent_auto_stop():
    """Spawn run_agent with auto-stop to ensure it exits within timeout."""
    env = os.environ.copy()
    env.setdefault("GEMINI_API_KEY", "test-key")
    env["DISABLE_CHAT_RESPONDER"] = "1"  # simplify
    env["DISABLE_INGEST"] = "1"  # no telemetry
    env["AGENT_AUTO_STOP_SECONDS"] = "1.5"
    # Short grace timeout
    cmd = [sys.executable, "scripts/run_agent.py", "--grace-timeout", "3"]
    start = time.time()
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        outs, errs = proc.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate(timeout=3)
        raise AssertionError(
            f"Agent did not exit. stdout={outs.decode()[:400]} stderr={errs.decode()[:400]}"
        )
    duration = time.time() - start
    assert (
        proc.returncode == 0
    ), f"Non-zero exit code {proc.returncode}: stderr={errs.decode()[:400]}"
    assert duration < 7, f"Agent took too long to exit: {duration:.2f}s"

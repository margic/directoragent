import os
import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_gemini_live_session_basic():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set; skipping live Gemini integration test")
    try:  # defer import until we know key present to avoid unused import when skipped
        from google import genai  # type: ignore  # noqa: F401
    except Exception:  # pragma: no cover
        pytest.skip("google-genai package not installed")
    # Avoid function calls for a lightweight smoke test
    os.environ.setdefault("GEMINI_DISABLE_CALLS", "1")
    from sim_racecenter_agent.director.gemini_direct import GeminiToolSession

    session = GeminiToolSession()
    count = await session.ensure_started()
    assert count > 0
    reply = await session.ask("Hello", enable_function_calls=False)
    assert isinstance(reply, str) and len(reply) > 0
    await session.close()

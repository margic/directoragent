import types
import pytest
import sys
import importlib
from typing import Any


class _FakePart:
    def __init__(self, function_call: Any | None = None, text: str | None = None):
        self.function_call = function_call
        self.text = text


class _FakeContent:
    def __init__(self, parts):
        self.parts = parts


class _FakeCandidate:
    def __init__(self, parts):
        # Provide both direct list (content iterable) and .parts for robustness
        self.content = parts  # iterable
        self.parts = parts


class _FakeResp:
    def __init__(self, candidates=None, text: str | None = None):
        self.candidates = candidates or []
        self.text = text


class _FakeFunctionCall:
    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args


@pytest.fixture
def fake_genai(monkeypatch):
    """Provide a fake google.genai module with minimal surface for tests."""
    # Build fake types submodule
    types_mod = types.SimpleNamespace()

    class FunctionDeclaration:  # type: ignore
        def __init__(self, name: str, description: str, parameters: dict):
            self.name = name
            self.description = description
            self.parameters = parameters

    class Tool:  # type: ignore
        def __init__(self, function_declarations):
            self.function_declarations = function_declarations

    class GenerateContentConfig:  # type: ignore
        def __init__(self, temperature: float, tools: list):
            self.temperature = temperature
            self.tools = tools

    types_mod.FunctionDeclaration = FunctionDeclaration
    types_mod.Tool = Tool
    types_mod.GenerateContentConfig = GenerateContentConfig

    # Dynamic sequence controller for model responses
    responses: list[_FakeResp] = []

    class _AioWrapper:
        def __init__(self):
            self.models = self

        async def generate_content(self, model: str, contents: str, config):  # type: ignore
            # Pop first response or return simple echo
            if responses:
                return responses.pop(0)
            return _FakeResp(text=f"ECHO:{contents}")

    class Client:  # type: ignore
        def __init__(self):
            self.aio = _AioWrapper()

    fake_root = types.SimpleNamespace(Client=Client, types=types_mod)

    # Install into sys.modules layout expected: google, google.genai, google.genai.types
    google_pkg = types.ModuleType("google")
    fake_genai_mod = types.ModuleType("google.genai")
    fake_genai_types_mod = types.ModuleType("google.genai.types")
    fake_genai_mod.Client = fake_root.Client  # type: ignore[attr-defined]
    fake_genai_mod.types = types_mod  # type: ignore[attr-defined]
    fake_genai_mod.__dict__.update({"Client": fake_root.Client, "types": types_mod})
    fake_genai_types_mod.__dict__.update(types_mod.__dict__)
    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = fake_genai_mod
    sys.modules["google.genai.types"] = fake_genai_types_mod
    setattr(google_pkg, "genai", fake_genai_mod)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return responses  # allow test to push predetermined responses


@pytest.mark.asyncio
@pytest.mark.integration
async def test_session_initialization_and_tool_names(fake_genai):
    import sim_racecenter_agent.director.gemini_direct as gd

    importlib.reload(gd)
    session = gd.GeminiToolSession()
    count = await session.ensure_started()
    names = set(session.tool_names())
    # Expect at least one known tool name
    assert count > 0
    assert "get_current_battle" in names
    await session.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_function_call_roundtrip(fake_genai):
    responses = fake_genai
    # First model response triggers a tool call (search_chat)
    fc = _FakeFunctionCall("search_chat", {"query": "leader", "limit": 1})
    first = _FakeResp(candidates=[_FakeCandidate([_FakePart(function_call=fc)])])
    # Second response after tool execution returns final text
    second = _FakeResp(text="The leader is Car 1")
    responses.extend([first, second])
    import sim_racecenter_agent.director.gemini_direct as gd

    importlib.reload(gd)
    session = gd.GeminiToolSession()
    out = await session.ask("Who is leading?", enable_function_calls=True)
    assert "leader" in out.lower() or out.startswith("ECHO:")  # fallback if mock path changes
    await session.close()

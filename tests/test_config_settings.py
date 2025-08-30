import importlib


def reload_settings_module():
    import sim_racecenter_agent.config.settings as settings_mod

    importlib.reload(settings_mod)
    return settings_mod


def test_default_settings_values(monkeypatch):
    # Ensure env clean for keys we assert
    for key in [
        "NATS_URL",
        "LLM_PLANNER_MODEL",
        "LLM_ANSWER_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)
    settings_mod = reload_settings_module()
    s = settings_mod.get_settings()
    assert s.nats.url.startswith("nats://"), "Unexpected default NATS URL"
    assert s.llm_answer_model
    assert s.llm_planner_model


def test_env_override(monkeypatch):
    monkeypatch.setenv("NATS_URL", "nats://localhost:4223")
    monkeypatch.setenv("LLM_ANSWER_MODEL", "gemini-custom")
    settings_mod = reload_settings_module()
    s = settings_mod.get_settings()
    assert s.nats.url.endswith(":4223")
    assert s.llm_answer_model == "gemini-custom"


def test_boolean_feature_flags(monkeypatch):
    monkeypatch.setenv("ENABLE_EXTENDED_STANDINGS", "0")
    monkeypatch.setenv("ENABLE_SESSION_STATE", "0")
    settings_mod = reload_settings_module()
    s = settings_mod.get_settings()
    assert s.enable_extended_standings is False
    assert s.enable_session_state is False

import os
from sim_racecenter_agent.config.settings import get_settings, NATSSettings


def test_nats_timeout_config():
    """Test that NATS timeout configuration works correctly"""
    # Test default value
    settings = NATSSettings()
    assert settings.connect_timeout == 10.0

    # Test environment variable is read correctly
    current_timeout = os.environ.get("NATS_CONNECT_TIMEOUT")
    if current_timeout:
        settings = get_settings()
        assert settings.nats.connect_timeout == float(current_timeout)
        print(f"✅ NATS_CONNECT_TIMEOUT={current_timeout} correctly loaded")

    # Test manual configuration
    manual_settings = NATSSettings(connect_timeout=5.5)
    assert manual_settings.connect_timeout == 5.5


def test_nats_environment_variable_support():
    """Test that all NATS environment variables are supported"""
    # Save original values
    original_vars = {}
    test_vars = {
        "NATS_URL": "nats://test:4222",
        "NATS_USERNAME": "testuser",
        "NATS_PASSWORD": "testpass",
        "NATS_CONNECT_TIMEOUT": "3.5",
    }

    for var in test_vars:
        original_vars[var] = os.environ.get(var)
        os.environ[var] = test_vars[var]

    try:
        settings = get_settings()
        assert settings.nats.url == "nats://test:4222"
        assert settings.nats.username == "testuser"
        assert settings.nats.password == "testpass"
        assert settings.nats.connect_timeout == 3.5
        print("✅ All NATS environment variables correctly parsed")
    finally:
        # Restore original values
        for var, original_val in original_vars.items():
            if original_val is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = original_val

import pytest
from src.research_system.config import Settings, get_settings


def test_settings_defaults():
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test_openrouter_key",
        tavily_api_key="test_tavily_key",
    )
    assert settings.model_name == "openrouter/free"
    assert settings.tavily_k == 5
    assert settings.max_chars_per_page == 8000
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"


def test_settings_validation_missing_keys():
    settings = Settings(openrouter_api_key="", tavily_api_key="")
    with pytest.raises(ValueError, match="Missing or placeholder API keys"):
        settings.validate_api_keys()


def test_settings_validation_placeholder_keys():
    settings = Settings(
        openrouter_api_key="your_openrouter_key",
        tavily_api_key="your_tavily_key",
    )
    with pytest.raises(ValueError, match="Missing or placeholder API keys"):
        settings.validate_api_keys()


def test_settings_validation_success():
    settings = Settings(
        openrouter_api_key="sk-or-v1-validkey12345",
        tavily_api_key="tvly-validkey12345",
    )
    # Should not raise
    settings.validate_api_keys()


def test_get_settings_singleton():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2

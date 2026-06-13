"""Tests for Settings loader."""

import pytest
from pydantic import ValidationError

from analytis.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYTIS_DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("ANALYTIS_API_KEY", "secret-key")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/d"
    assert settings.api_key.get_secret_value() == "secret-key"
    assert settings.log_level == "INFO"
    assert settings.log_format == "console"


def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANALYTIS_DATABASE_URL", raising=False)
    monkeypatch.delenv("ANALYTIS_API_KEY", raising=False)
    # Override env_file so a real .env in the repo doesn't satisfy the requirements.
    monkeypatch.setitem(Settings.model_config, "env_file", None)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_log_level_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYTIS_DATABASE_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("ANALYTIS_API_KEY", "x")
    monkeypatch.setenv("ANALYTIS_LOG_LEVEL", "TRACE")

    with pytest.raises(ValidationError):
        Settings()

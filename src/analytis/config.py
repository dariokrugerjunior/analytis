"""Centralized application configuration loaded from environment."""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — single source of truth for env-driven config."""

    model_config = SettingsConfigDict(
        env_prefix="ANALYTIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    api_key: SecretStr

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    football_data_api_key: SecretStr | None = None
    elo_ratings_url: str = "http://www.eloratings.net/World.tsv"
    the_odds_api_key: SecretStr | None = None
    the_odds_api_base_url: str = "https://api.the-odds-api.com/v4"

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    auto_ingest_enabled: bool = True
    auto_ingest_competition: str = "2000"
    auto_ingest_season: str = "2026"
    auto_ingest_interval_seconds: int = 120
    auto_ingest_window_before_kickoff_minutes: int = 30
    auto_ingest_window_after_kickoff_minutes: int = 180


def get_settings() -> Settings:
    """Factory for DI — keeps `Settings()` call in one place."""
    return Settings()

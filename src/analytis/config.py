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


def get_settings() -> Settings:
    """Factory for DI — keeps `Settings()` call in one place."""
    return Settings()

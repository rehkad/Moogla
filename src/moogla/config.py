from __future__ import annotations

import secrets
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model: str = Field("gpt-3.5-turbo", validation_alias="MOOGLA_MODEL")
    openai_api_key: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")
    openai_api_base: Optional[str] = Field(None, validation_alias="OPENAI_API_BASE")
    server_api_key: Optional[str] = Field(None, validation_alias="MOOGLA_API_KEY")
    rate_limit: Optional[int] = Field(None, validation_alias="MOOGLA_RATE_LIMIT")
    redis_url: str = Field(
        "redis://localhost:6379", validation_alias="MOOGLA_REDIS_URL"
    )
    db_url: str = Field("sqlite:///:memory:", validation_alias="MOOGLA_DB_URL")
    plugin_file: Optional[Path] = Field(None, validation_alias="MOOGLA_PLUGIN_FILE")
    jwt_secret: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        validation_alias="MOOGLA_JWT_SECRET",
    )
    token_exp_minutes: int = Field(30, validation_alias="MOOGLA_TOKEN_EXP_MINUTES")
    model_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "moogla" / "models",
        validation_alias="MOOGLA_MODEL_DIR",
    )
    cors_origins: Optional[str] = Field(
        None, validation_alias="MOOGLA_CORS_ORIGINS"
    )
    log_level: str = Field("INFO", validation_alias="MOOGLA_LOG_LEVEL")

    model_config = SettingsConfigDict(env_prefix="")

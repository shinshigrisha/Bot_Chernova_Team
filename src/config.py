"""Application configuration from environment."""
import json
from functools import lru_cache
from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class S3Settings(BaseSettings):
    """S3/MinIO storage settings."""

    endpoint_url: str = Field(default="http://minio:9000", alias="S3_ENDPOINT")
    access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    bucket: str = Field(default="delivery-assistant", alias="S3_BUCKET")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    timezone: str = Field(default="Europe/Moscow", alias="TIMEZONE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:pass@postgres:5432/delivery_assistant",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # Celery
    celery_broker_url: str = Field(
        default="redis://redis:6379/1",
        alias="CELERY_BROKER_URL",
    )

    # S3/MinIO
    s3: S3Settings = Field(default_factory=S3Settings)

    # AI
    ai_enabled: bool = Field(default=False, alias="AI_ENABLED")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, list, int]) -> List[int]:
        if isinstance(v, int):
            return [v]
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                return [int(x) for x in parsed]
            return [int(x.strip()) for x in stripped.split(",") if x.strip()]
        return []


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()

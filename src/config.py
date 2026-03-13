"""Application configuration from environment."""
import json
from functools import lru_cache
from typing import List, Union
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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
    database_ssl: bool = Field(default=False, alias="DATABASE_SSL")

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url_sslmode(cls, v: str) -> str:
        """Strip sslmode/ssl_mode from URL so SQLAlchemy+asyncpg don't get invalid or unsupported kwargs.
        asyncpg.connect() does not accept sslmode as a keyword when called via SQLAlchemy; invalid values
        cause ClientConfigurationError. Removing these params lets asyncpg use its default connection behavior."""
        scheme = (v.split(":")[0] or "").lower()
        if "postgres" not in scheme:
            return v
        parsed = urlparse(v)
        if not parsed.query:
            return v
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("sslmode", None)
        params.pop("ssl_mode", None)
        if not params:
            return urlunparse(parsed._replace(query=""))
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # Celery
    celery_broker_url: str = Field(
        default="redis://redis:6379/1",
        alias="CELERY_BROKER_URL",
    )

    # S3/MinIO
    s3: S3Settings = Field(default_factory=S3Settings)

    # AI: core switches and legacy provider settings
    ai_enabled: bool = Field(default=False, alias="AI_ENABLED")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        alias="DEEPSEEK_BASE_URL",
    )
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    # OpenAI-compatible endpoint (canonical entry point)
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")

    # Canonical multi-model routing by capability (provider + model)
    ai_default_provider: str = Field(
        default="openai_compatible",
        alias="AI_DEFAULT_PROVIDER",
    )
    ai_default_model: str = Field(
        default="gpt-5-mini",
        alias="AI_DEFAULT_MODEL",
    )

    ai_fast_provider: str = Field(
        default="openai_compatible",
        alias="AI_FAST_PROVIDER",
    )
    ai_fast_model: str = Field(
        default="gpt-5-mini",
        alias="AI_FAST_MODEL",
    )

    ai_reasoning_provider: str = Field(
        default="openai_compatible",
        alias="AI_REASONING_PROVIDER",
    )
    ai_reasoning_model: str = Field(
        default="gpt-5-chat-latest",
        alias="AI_REASONING_MODEL",
    )

    ai_analytics_provider: str = Field(
        default="openai_compatible",
        alias="AI_ANALYTICS_PROVIDER",
    )
    ai_analytics_model: str = Field(
        default="gpt-5-chat-latest",
        alias="AI_ANALYTICS_MODEL",
    )

    ai_fallback_provider: str = Field(
        default="openai_compatible",
        alias="AI_FALLBACK_PROVIDER",
    )
    ai_fallback_model: str = Field(
        default="gpt-5-nano",
        alias="AI_FALLBACK_MODEL",
    )

    # Embeddings configuration (kept local by default)
    embedding_provider: str = Field(
        default="local",
        alias="EMBEDDING_PROVIDER",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )

    # Budget / safety limits
    ai_max_output_tokens: int = Field(
        default=220,
        alias="AI_MAX_OUTPUT_TOKENS",
    )
    ai_max_context_items: int = Field(
        default=3,
        alias="AI_MAX_CONTEXT_ITEMS",
    )

    # Feature flags for AI capabilities
    ai_enable_heavy_analytics: bool = Field(
        default=False,
        alias="AI_ENABLE_HEAVY_ANALYTICS",
    )
    ai_enable_analytics_assistant: bool = Field(
        default=True,
        alias="AI_ENABLE_ANALYTICS_ASSISTANT",
    )
    ai_enable_rag: bool = Field(
        default=True,
        alias="AI_ENABLE_RAG",
    )
    ai_enable_semantic_search: bool = Field(
        default=True,
        alias="AI_ENABLE_SEMANTIC_SEARCH",
    )

    # Access / auth
    enable_new_auth_flow: bool = Field(
        default=False,
        alias="ENABLE_NEW_AUTH_FLOW",
    )

    # Feature flags (expand → migrate → switch → cleanup)
    enable_menu_v2: bool = Field(default=True, alias="ENABLE_MENU_V2")
    enable_verification_notifications: bool = Field(
        default=True,
        alias="ENABLE_VERIFICATION_NOTIFICATIONS",
    )
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    enable_admin_menu_v2: bool = Field(default=False, alias="ENABLE_ADMIN_MENU_V2")
    enable_ai_chat_v2: bool = Field(default=False, alias="ENABLE_AI_CHAT_V2")
    enable_faq_semantic_search: bool = Field(
        default=False,
        alias="ENABLE_FAQ_SEMANTIC_SEARCH",
    )
    enable_rag_assistant: bool = Field(default=False, alias="ENABLE_RAG_ASSISTANT")

    # n8n integration (optional pilot)
    n8n_verification_mirror_enabled: bool = Field(
        default=False,
        alias="N8N_VERIFICATION_MIRROR_ENABLED",
    )
    n8n_verification_webhook_url: str = Field(
        default="",
        alias="N8N_VERIFICATION_WEBHOOK_URL",
    )

    # Automation webhook (n8n / external): HTTP server for POST /automation/event (0 = disabled)
    automation_http_port: int = Field(default=0, alias="AUTOMATION_HTTP_PORT")

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

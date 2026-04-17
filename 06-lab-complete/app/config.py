"""Application configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    app_name: str = Field(default="Production AI Agent", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")

    llm_model: str = Field(default="mock-llm", alias="LLM_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    agent_api_key: str = Field(default="secret", alias="AGENT_API_KEY")
    jwt_secret: str = Field(default="dev-jwt-secret", alias="JWT_SECRET")
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
    admin_users: str = Field(default="admin", alias="ADMIN_USERS")

    rate_limit_per_minute: int = Field(default=10, alias="RATE_LIMIT_PER_MINUTE")
    monthly_budget_usd: float = Field(default=10.0, alias="MONTHLY_BUDGET_USD")

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    history_max_messages: int = Field(default=20, alias="HISTORY_MAX_MESSAGES")
    history_ttl_seconds: int = Field(default=2592000, alias="HISTORY_TTL_SECONDS")


settings = Settings()

"""Application settings using Pydantic."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="NANOBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")

    # LLM settings
    llm_model: str = Field(default="gpt-4", description="LLM model name")
    llm_api_key: str = Field(default="", description="LLM API key")
    llm_base_url: str | None = Field(default=None, description="LLM API base URL")

    # Session settings
    session_storage_path: str = Field(
        default="./workspace/sessions", description="Session storage path"
    )
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")

    # RAG settings
    rag_enabled: bool = Field(default=True, description="Enable RAG tool")
    rag_embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model"
    )
    rag_vector_db: str = Field(default="chromadb", description="Vector database type")

    # SQL settings
    sql_enabled: bool = Field(default=True, description="Enable SQL tool")
    sql_connections: dict[str, str] = Field(
        default_factory=lambda: {"main": "sqlite:///./data/main.db"},
        description="Database connections",
    )

    # Time series settings
    ts_enabled: bool = Field(default=True, description="Enable time series tool")
    ts_default_model: str = Field(default="prophet", description="Default forecasting model")

    # API settings
    api_key: str = Field(default="", description="API key for authentication")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"], description="CORS allowed origins"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

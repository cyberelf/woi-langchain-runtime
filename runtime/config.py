"""Configuration management for the runtime service."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Authentication
    runtime_token: str = Field(default="test_token", alias="RUNTIME_TOKEN")

    # LLM Proxy configuration
    llm_proxy_url: Optional[str] = Field(default=None, alias="LLM_PROXY_URL")
    llm_proxy_token: Optional[str] = Field(default=None, alias="LLM_PROXY_TOKEN")

    # OpenAI configuration (fallback if LLM proxy not available)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")

    # Runtime limits
    max_concurrent_agents: int = Field(default=100, alias="MAX_CONCURRENT_AGENTS")
    max_message_length: int = Field(default=32000, alias="MAX_MESSAGE_LENGTH")
    max_conversation_history: int = Field(default=100, alias="MAX_CONVERSATION_HISTORY")

    # Execution timeouts
    agent_execution_timeout: int = Field(default=300, alias="AGENT_EXECUTION_TIMEOUT")
    llm_request_timeout: int = Field(default=60, alias="LLM_REQUEST_TIMEOUT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Development
    debug: bool = Field(default=False, alias="DEBUG")
    reload: bool = Field(default=False, alias="RELOAD")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()

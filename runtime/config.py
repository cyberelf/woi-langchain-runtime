"""Configuration management for the runtime service."""

import os
from typing import Optional

from pydantic import BaseSettings, Field
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Authentication
    runtime_token: str = Field(..., env="RUNTIME_TOKEN")
    
    # LLM Proxy configuration
    llm_proxy_url: str = Field(..., env="LLM_PROXY_URL")
    llm_proxy_token: Optional[str] = Field(default=None, env="LLM_PROXY_TOKEN")
    
    # OpenAI configuration (fallback if LLM proxy not available)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    
    # Runtime limits
    max_concurrent_agents: int = Field(default=100, env="MAX_CONCURRENT_AGENTS")
    max_message_length: int = Field(default=32000, env="MAX_MESSAGE_LENGTH")
    max_conversation_history: int = Field(default=100, env="MAX_CONVERSATION_HISTORY")
    
    # Execution timeouts
    agent_execution_timeout: int = Field(default=300, env="AGENT_EXECUTION_TIMEOUT")
    llm_request_timeout: int = Field(default=60, env="LLM_REQUEST_TIMEOUT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Development
    debug: bool = Field(default=False, env="DEBUG")
    reload: bool = Field(default=False, env="RELOAD")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Global settings instance
settings = Settings() 
"""Configuration management for the runtime service."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from runtime.core import agent_orchestrator


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
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPL_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Runtime limits
    max_concurrent_agents: int = Field(default=100, alias="MAX_CONCURRENT_AGENTS")
    max_message_length: int = Field(default=32000, alias="MAX_MESSAGE_LENGTH")
    max_conversation_history: int = Field(default=100, alias="MAX_CONVERSATION_HISTORY")

    # Execution timeouts
    agent_execution_timeout: int = Field(default=30, alias="AGENT_EXECUTION_TIMEOUT")
    llm_request_timeout: int = Field(default=60, alias="LLM_REQUEST_TIMEOUT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Development
    debug: bool = Field(default=False, alias="DEBUG")
    reload: bool = Field(default=False, alias="RELOAD")
    
    @property
    def effective_log_level(self) -> str:
        """Get the effective log level based on debug setting.
        
        If debug is True, use DEBUG level unless LOG_LEVEL is explicitly set to something else.
        If debug is False, use the configured log_level (default INFO).
        """
        # If LOG_LEVEL env var is explicitly set and differs from default, use it
        import os
        if "LOG_LEVEL" in os.environ:
            return self.log_level
        
        # Otherwise, let debug setting control the log level
        return "DEBUG" if self.debug else "INFO"
    
    # Framework configuration
    default_framework: str = Field(default="langgraph", alias="DEFAULT_FRAMEWORK")
    enabled_frameworks: str = Field(default="langgraph", alias="ENABLED_FRAMEWORKS")  # Comma-separated

    # Task management configuration
    task_manager_enabled: bool = Field(default=True, alias="TASK_MANAGER_ENABLED")
    task_manager_workers: int = Field(default=10, alias="TASK_MANAGER_WORKERS")
    task_cleanup_interval: int = Field(default=3600, alias="TASK_CLEANUP_INTERVAL")  # seconds
    instance_timeout: int = Field(default=7200, alias="INSTANCE_TIMEOUT")  # seconds
    
    # Message queue configuration
    message_queue_type: str = Field(default="memory", alias="MESSAGE_QUEUE_TYPE")  # memory, redis, rabbitmq
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    rabbitmq_url: str = Field(default="amqp://localhost:5672", alias="RABBITMQ_URL")
    
    # Message queue limits
    max_queue_size: int = Field(default=10000, alias="MAX_QUEUE_SIZE")
    message_retention_hours: int = Field(default=24, alias="MESSAGE_RETENTION_HOURS")
    
    # Services configuration file
    services_config_file: Optional[str] = Field(
        default="config/services-config.json", alias="SERVICES_CONFIG_FILE"
    )
    services_config_json: str = Field(default="{}", alias="SERVICES_CONFIG")  # Fallback JSON string

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()

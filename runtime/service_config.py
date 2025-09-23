"""Service configuration using pydantic-settings."""

from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceConfig(BaseSettings):
    """Service configurations for LLM, toolsets, etc."""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    reload: bool = Field(default=False, alias="RELOAD")
    
    # Authentication
    runtime_token: str = Field(default="your-runtime-token-here", alias="RUNTIME_TOKEN")
    
    # LLM Proxy Configuration
    llm_proxy_url: str = Field(default="http://localhost:8001", alias="LLM_PROXY_URL")
    llm_proxy_token: str = Field(default="your-llm-proxy-token", alias="LLM_PROXY_TOKEN")
    
    # OpenAI Configuration (Fallback)
    openai_api_key: str = Field(default="your-openai-api-key", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    
    # Runtime Limits
    max_concurrent_agents: int = Field(default=100, alias="MAX_CONCURRENT_AGENTS")
    max_message_length: int = Field(default=32000, alias="MAX_MESSAGE_LENGTH")
    max_conversation_history: int = Field(default=100, alias="MAX_CONVERSATION_HISTORY")
    
    # Execution Timeouts (seconds)
    agent_execution_timeout: int = Field(default=300, alias="AGENT_EXECUTION_TIMEOUT")
    llm_request_timeout: int = Field(default=60, alias="LLM_REQUEST_TIMEOUT")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Service configuration as JSON string or dict
    services_config: str = Field(default="{}", alias="SERVICES_CONFIG")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )
    
    def get_config_dict(self) -> dict[str, Any]:
        """Get services configuration as dictionary."""
        import json
        try:
            if isinstance(self.services_config, str):
                return json.loads(self.services_config)
            return self.services_config
        except json.JSONDecodeError:
            return {}
    
    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM service configuration."""
        return self.get_config_dict().get("llm", {})
    
    def get_toolset_config(self) -> dict[str, Any]:
        """Get toolset service configuration."""
        return self.get_config_dict().get("toolsets", {})


# Global service config instance
service_config = ServiceConfig()

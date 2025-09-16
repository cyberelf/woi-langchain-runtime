"""Service configuration using pydantic-settings."""

from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceConfig(BaseSettings):
    """Service configurations for LLM, toolsets, etc."""
    
    # Service configuration as JSON string or dict
    services_config: str = Field(default="{}", alias="SERVICES_CONFIG")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get services configuration as dictionary."""
        import json
        try:
            if isinstance(self.services_config, str):
                return json.loads(self.services_config)
            return self.services_config
        except json.JSONDecodeError:
            return {}
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM service configuration."""
        return self.get_config_dict().get("llm", {})
    
    def get_toolset_config(self) -> Dict[str, Any]:
        """Get toolset service configuration."""
        return self.get_config_dict().get("toolsets", {})


# Global service config instance
service_config = ServiceConfig()

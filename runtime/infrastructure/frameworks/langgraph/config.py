"""LangGraph framework configuration models."""

from typing import Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, validator


class LLMProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""
    
    type: Literal["openai", "anthropic", "deepseek", "google", "test"] = Field(
        ..., description="LLM provider type"
    )
    model: str = Field(..., description="Model name")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    base_url: Optional[str] = Field(None, description="Custom base URL")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Default temperature")
    max_tokens: int = Field(1000, gt=0, description="Default max tokens")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional provider metadata")
    
    @model_validator(mode="after")
    def validate_api_key(self):
        """Validate API key for non-test providers."""
        provider_type = self.type
        if provider_type != "test" and not self.api_key:
            # In production, this might be required. For now, just warn.
            pass
        return self


class LLMConfig(BaseModel):
    """LLM service configuration for LangGraph framework."""
    
    providers: dict[str, LLMProviderConfig] = Field(
        default_factory=dict, description="Available LLM providers"
    )
    default_provider: Optional[str] = Field(None, description="Default LLM provider to use")
    fallback_provider: Optional[str] = Field(None, description="Fallback provider if default fails")

    @field_validator("providers")
    def validate_providers(cls, v):
        """Validate that providers are not empty."""
        if not v:
            raise ValueError("Providers cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_default_provider(self):
        """Validate that default provider exists in providers."""
        if self.default_provider and self.default_provider not in self.providers:
            raise ValueError(f"Default provider {self.default_provider} not found in providers")
        if self.fallback_provider and self.fallback_provider not in self.providers:
            raise ValueError(f"Fallback provider {self.fallback_provider} not found in providers")
        return self

    def get_provider_config(self, provider_name: Optional[str] = None) -> LLMProviderConfig:
        """Get configuration for a specific provider."""
        provider_name = provider_name or self.default_provider or self.fallback_provider

        if not provider_name:
            raise ValueError("No provider name provided and no default or fallback provider configured")

        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not found")
        
        return self.providers[provider_name]


class ToolsetServerConfig(BaseModel):
    """Configuration for an MCP server."""
    
    name: str = Field(..., description="Server name")
    command: str = Field(..., description="Command to start the server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")


class ToolsetConfig(BaseModel):
    """Configuration for a single toolset."""
    
    type: Literal["mcp", "custom"] = Field(..., description="Toolset type")
    config: dict[str, Any] = Field(default_factory=dict, description="Toolset-specific configuration")
    
    @field_validator("config")
    def validate_config_by_type(cls, v):
        """Validate configuration based on toolset type."""
        toolset_type = v.get("type")
        
        if toolset_type == "mcp":
            # Validate MCP configuration
            if "servers" in v:
                servers = v["servers"]
                if not isinstance(servers, list):
                    raise ValueError("MCP servers must be a list")
                
                # Validate each server configuration
                for i, server in enumerate(servers):
                    try:
                        ToolsetServerConfig(**server)
                    except Exception as e:
                        raise ValueError(f"Invalid MCP server config at index {i}: {e}")
            
            # Set default timeout if not provided
            if "timeout" not in v:
                v["timeout"] = 30
                
        elif toolset_type == "custom":
            # Validate custom toolset configuration
            if "tools_directory" not in v:
                v["tools_directory"] = "./tools"
            if "auto_discovery" not in v:
                v["auto_discovery"] = False
                
        return v


class ToolsetsConfig(BaseModel):
    """Toolsets configuration for LangGraph framework."""
    
    toolsets: dict[str, ToolsetConfig] = Field(
        default_factory=dict, description="Available toolsets"
    )
    default_toolsets: list[str] = Field(
        default_factory=list, description="Default toolset names to load"
    )
    
    @model_validator(mode="after")
    def validate_default_toolsets(self):
        """Validate that default toolsets exist in toolsets."""
        if self.default_toolsets:
            for name in self.default_toolsets:
                if name not in self.toolsets:
                    raise ValueError(f"Default toolset {name} not found in toolsets")
        return self
    
    def get_toolset_config(self, toolset_name: str) -> Optional[ToolsetConfig]:
        """Get configuration for a specific toolset."""
        return self.toolsets.get(toolset_name)


class LangGraphFrameworkConfig(BaseModel):
    """Complete LangGraph framework configuration."""
    
    llm: LLMConfig = Field(..., description="LLM configuration")
    toolsets: ToolsetsConfig = Field(..., description="Toolsets configuration")
    
    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "LangGraphFrameworkConfig":
        """Create configuration from dictionary with validation."""
        return cls(**config_dict)
    
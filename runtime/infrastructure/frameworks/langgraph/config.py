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


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server following LangChain MCP spec.
    
    See: https://docs.langchain.com/oss/python/langchain/mcp
    """
    
    name: str = Field(..., description="Server name")
    transport: Literal["stdio", "streamable_http", "sse"] = Field(
        default="stdio", description="Transport type"
    )
    url: Optional[str] = Field(default=None, description="URL for HTTP-based transports")
    command: Optional[str] = Field(default=None, description="Command to start the server (for stdio)")
    args: list[str] = Field(default_factory=list, description="Command arguments (for stdio)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    timeout: int = Field(30, gt=0, description="Operation timeout in seconds")
    
    @model_validator(mode="after")
    def validate_transport_requirements(self):
        """Validate that required fields are provided for each transport type."""
        if self.transport == "stdio" and not self.command:
            raise ValueError("Command is required for stdio transport")
        if self.transport in ["streamable_http", "sse"] and not self.url:
            raise ValueError(f"URL is required for {self.transport} transport")
        return self


class MCPToolsetConfig(BaseModel):
    """Configuration for MCP-based toolsets."""
    
    servers: list[MCPServerConfig] = Field(
        default_factory=list, description="List of MCP servers"
    )
    
    @field_validator("servers")
    def validate_servers(cls, v):
        """Validate that at least one server is configured."""
        if not v:
            raise ValueError("At least one MCP server must be configured")
        return v


class ToolsetsConfig(BaseModel):
    """Toolsets configuration for LangGraph framework."""
    
    mcp: dict[str, MCPToolsetConfig] = Field(
        default_factory=dict, description="MCP-based toolsets"
    )
    custom: list[str] | Literal["all"] = Field(
        "all", description="Custom tool names or 'all' for all plugins"
    )
    default_toolsets: list[str] = Field(
        default_factory=list, description="Default toolset names to load"
    )
    
    @field_validator("custom")
    def validate_custom(cls, v):
        """Validate custom tools configuration."""
        if isinstance(v, str) and v != "all":
            raise ValueError("custom must be either a list of tool names or 'all'")
        if isinstance(v, list) and not v:
            raise ValueError("custom list cannot be empty")
        return v
    
    @model_validator(mode="after")
    def validate_default_toolsets(self):
        """Validate that default toolsets exist in mcp toolsets."""
        if self.default_toolsets:
            for name in self.default_toolsets:
                if name not in self.mcp:
                    raise ValueError(f"Default toolset {name} not found in mcp toolsets")
        return self
    
    def get_mcp_toolset(self, toolset_name: str) -> Optional[MCPToolsetConfig]:
        """Get MCP toolset configuration by name."""
        return self.mcp.get(toolset_name)


class LangGraphFrameworkConfig(BaseModel):
    """Complete LangGraph framework configuration."""
    
    llm: LLMConfig = Field(..., description="LLM configuration")
    toolsets: ToolsetsConfig = Field(..., description="Toolsets configuration")
    
    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "LangGraphFrameworkConfig":
        """Create configuration from dictionary with validation."""
        return cls(**config_dict)
    
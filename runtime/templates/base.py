"""Base agent template for framework-agnostic agent implementations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional

from runtime.domain.services.llm import LLMService
from runtime.domain.services.toolset import ToolsetService
from runtime.infrastructure.web.models.responses import (
    ChatCompletionChunk,
    ChatCompletionResponse,
)
from runtime.domain.value_objects.chat_message import ChatMessage
from runtime.domain.value_objects.agent_configuration import AgentConfiguration


class BaseAgentTemplate(ABC):
    """Base class for all agent templates.
    
    Agent templates define both template metadata (as class variables) 
    and execution logic (as instance methods).
    """

    # Template Metadata (should be overridden in subclasses)
    template_name: str = "Base Agent Template"
    template_id: str = "base-agent"
    template_version: str = "1.0.0"
    template_description: str = "Base agent template"
    framework: str = "base"

    def __init__(
        self, 
        configuration: AgentConfiguration, 
        llm_service: LLMService, 
        toolset_service: Optional[ToolsetService] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize agent instance with configuration and metadata.
        
        Args:
            configuration: AgentConfiguration value object containing all agent config
            llm_service: LLM service instance
            toolset_service: Optional toolset service instance
            metadata: Static metadata about the agent (id, name, template_id, etc.)
            
        """
        metadata = metadata or {}
        
        # Initialize identity and template fields from metadata
        self.id = metadata.get("agent_id", "unknown")
        self.name = metadata.get("agent_name", "Unknown Agent")
        self.template_id = metadata.get("template_id", self.template_id)
        self.template_version = metadata.get("template_version", self.template_version)
        
        # Store the configuration value object
        self.agent_configuration = configuration
        
        # Get template configuration dict for backward compatibility
        self.template_config = configuration.get_template_configuration()
        
        # Services
        self.llm_service = llm_service
        self.toolset_service = toolset_service
        
        # Extract common config from AgentConfiguration
        self.system_prompt = configuration.system_prompt or ""
        self.llm_config_id = configuration.llm_config_id
        
        # Extract execution parameters from conversation_config
        self.default_temperature = configuration.get_temperature()
        self.default_max_tokens = configuration.get_max_tokens()
        
        # Extract conversation configuration
        self.max_history = (configuration.get_conversation_config_value("historyLength") or 
                           configuration.get_conversation_config_value("history_length"))
        
        # Extract toolset configuration (names only)
        self.toolset_configs = configuration.get_toolset_names()

    @abstractmethod
    async def execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """Execute the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream execute the agent. Must be implemented by subclasses."""
        pass

    async def get_llm_client(
        self, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """Get LLM client configured with execution parameters.
        
        This method merges template defaults with execution overrides and returns
        an LLM client configured with the effective parameters.
        
        Args:
            temperature: Override temperature (None to use template default)
            max_tokens: Override max_tokens (None to use template default)
            
        Returns:
            LLM client configured with effective parameters
        """
        execution_params = {}
        
        # Use effective parameters (template defaults vs execution overrides)
        effective_temperature = self.get_effective_temperature(temperature)
        effective_max_tokens = self.get_effective_max_tokens(max_tokens)
        
        if effective_temperature is not None:
            execution_params["temperature"] = effective_temperature
        if effective_max_tokens is not None:
            execution_params["max_tokens"] = effective_max_tokens
            
        return await self.llm_service.get_client(
            self.llm_config_id, 
            **execution_params
        )

    async def get_toolset_client(self):
        """Get toolset client for this agent."""
        if self.toolset_service:
            # Use extracted toolset configs
            if not self.toolset_configs:
                # Return None if no toolsets configured - agents can handle this gracefully
                return None
            return await self.toolset_service.create_client(self.toolset_configs)
        else:
            # Return None if toolset service not configured - allows agents to work without tools
            return None

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from template_config.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check template_config first for backward compatibility
        if key in self.template_config:
            return self.template_config[key]
        
        # Then check AgentConfiguration's template_config
        return self.agent_configuration.get_template_config_value(key, default)
    
    def get_effective_temperature(self, override_temperature: Optional[float] = None) -> Optional[float]:
        """Get effective temperature, with execution override taking precedence.
        
        Args:
            override_temperature: Temperature from execution call
            
        Returns:
            Effective temperature to use
        """
        return override_temperature if override_temperature is not None else self.default_temperature
    
    def get_effective_max_tokens(self, override_max_tokens: Optional[int] = None) -> Optional[int]:
        """Get effective max_tokens, with execution override taking precedence.
        
        Args:
            override_max_tokens: Max tokens from execution call
            
        Returns:
            Effective max_tokens to use
        """
        return override_max_tokens if override_max_tokens is not None else self.default_max_tokens
    
    def has_toolsets(self) -> bool:
        """Check if any toolsets are configured."""
        return len(self.toolset_configs) > 0
    
    def get_toolset_names(self) -> list[str]:
        """Get list of configured toolset names."""
        return self.toolset_configs.copy()

    def cleanup(self):
        """Clean up agent resources if needed."""
        pass

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.template_name} ({self.id})"

    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return f"BaseAgentTemplate(id='{self.id}', template_id='{self.template_id}')"


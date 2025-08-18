"""Base agent template for framework-agnostic agent implementations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional

from runtime.infrastructure.web.models.responses import (
    ChatCompletionChunk,
    ChatCompletionResponse,
)
from runtime.domain.value_objects.chat_message import ChatMessage


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
        configuration: dict[str, Any], 
        metadata: Optional[dict[str, Any]] = None,
        llm_service=None, 
        toolset_service=None
    ) -> None:
        """Initialize agent instance with configuration and metadata.
        
        Args:
            configuration: Agent's static configuration (template_config)
            metadata: Static metadata about the agent (id, name, template_id, etc.)
            llm_service: Optional LLM service instance
            toolset_service: Optional toolset service instance
        """
        metadata = metadata or {}
        
        # Initialize identity and template fields from metadata
        self.id = metadata.get("agent_id", "unknown")
        self.name = metadata.get("agent_name", "Unknown Agent")
        self.template_id = metadata.get("template_id", self.template_id)
        self.template_version = metadata.get("template_version", self.template_version)
        
        # Store the configuration
        self.template_config = configuration
        
        # Services
        self.llm_service = llm_service
        self.toolset_service = toolset_service
        
        # Extract common config from configuration dict
        self.system_prompt = configuration.get("system_prompt", "")
        self.llm_config_id = configuration.get("llm_config_id")

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

    async def get_llm_client(self):
        """Get LLM client for this agent."""
        if self.llm_service:
            return await self.llm_service.get_client(self.llm_config_id)
        else:
            # Fallback - would be implemented based on your LLM integration
            raise NotImplementedError("LLM service not configured")

    async def get_toolset_client(self):
        """Get toolset client for this agent."""
        if self.toolset_service:
            # Get toolset configurations for this agent
            toolset_configs = self.template_config.get("toolset_configs", [])
            if not toolset_configs:
                # Return None if no toolsets configured - agents can handle this gracefully
                return None
            return await self.toolset_service.create_client(toolset_configs)
        else:
            # Return None if toolset service not configured - allows agents to work without tools
            return None

    def cleanup(self):
        """Clean up agent resources if needed."""
        pass

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.template_name} ({self.id})"

    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return f"BaseAgentTemplate(id='{self.id}', template_id='{self.template_id}')"


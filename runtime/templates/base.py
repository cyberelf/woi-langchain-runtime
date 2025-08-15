"""Base agent template for framework-agnostic agent implementations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional

from runtime.infrastructure.web.models.requests import CreateAgentRequest
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
        agent_data: CreateAgentRequest, 
        llm_service=None, 
        toolset_service=None
    ) -> None:
        """Initialize agent instance with configuration."""
        # Parse request into structured models for better separation of concerns
        identity = agent_data.get_identity()
        template = agent_data.get_template()
        config = agent_data.get_agent_configuration()
        
        # Initialize identity and template fields
        self.id = identity.id
        self.name = identity.name
        self.template_id = template.template_id
        self.template_version = template.get_template_version() or self.template_version
        self.template_config = config.config or {}
        
        # Services
        self.llm_service = llm_service
        self.toolset_service = toolset_service
        
        # Extract common config using structured configuration model
        self.system_prompt = config.system_prompt or self.template_config.get("system_prompt", "")
        self.llm_config_id = config.llm_config_id or self.template_config.get("llm_config_id")

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

    def cleanup(self):
        """Clean up agent resources if needed."""
        pass

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.template_name} ({self.id})"

    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return f"BaseAgentTemplate(id='{self.id}', template_id='{self.template_id}')"


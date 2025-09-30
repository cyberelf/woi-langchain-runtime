"""Core executor interfaces and types.

These are the domain-level abstractions that define how agent execution works,
independent of any specific framework implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from collections.abc import AsyncGenerator
from datetime import datetime, UTC

from pydantic import BaseModel, Field, computed_field

from ..types import ChatMessage


class ExecutionResult(BaseModel):
    """Result of agent message execution - unified result type for A2A compatibility."""
    
    success: bool
    message: Optional[str] = None
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    processing_time_ms: int = 0
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    context_updated: bool = False
    
    message_id: Optional[str] = None  # Single atomic execution (A2A Message)
    task_id: Optional[str] = None     # Stateful conversation (A2A Task)
    agent_id: Optional[str] = None    # Agent that processed this
    context_id: Optional[str] = None   # Broader grouping context
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    @computed_field
    @property
    def total_tokens(self) -> int:
        """Total tokens = prompt + completion."""
        return self.prompt_tokens + self.completion_tokens


class StreamingChunk(BaseModel):
    """Streaming execution chunk - part of an A2A Message."""
    
    content: str
    chunk_index: int = 0
    finish_reason: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    message_id: Optional[str] = None  # The message this chunk belongs to  (A2A Message)
    task_id: Optional[str] = None      # The task this chunk belongs to (A2A Task)
    agent_id: Optional[str] = None     # Agent that produced this chunk
    context_id: Optional[str] = None    # Broader grouping context
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutionContext(BaseModel):
    """Context for agent execution - carries state between calls (A2A Task context)."""
    
    agent_id: str
    task_id: Optional[str] = None  # A2A Task ID (stateful conversation)
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    context_id: Optional[str] = None  # Broader grouping context
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0  # Renamed from execution_count
    
    def update(self, new_messages: list[ChatMessage], response_message: Optional[ChatMessage] = None):
        """Update context with new messages."""
        self.conversation_history.extend(new_messages)
        if response_message:
            self.conversation_history.append(response_message)
        self.last_updated = datetime.now(UTC)
        self.message_count += 1
        
        # Trim history if too long (configurable)
        max_history = self.metadata.get('max_history_length', 50)
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]


class AgentExecutorInterface(ABC):
    """Pure agent executor interface - stateless execution only.
    
    This interface defines how to execute agents without any framework-specific details.
    All implementations should be stateless and thread-safe.
    """
    
    @abstractmethod
    async def execute(
        self,
        template_id: str,
        template_version: str,
        configuration: dict[str, Any],
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute agent with given parameters - stateless execution."""
        pass
    
    @abstractmethod
    async def stream_execute(
        self,
        template_id: str,
        template_version: str,
        configuration: dict[str, Any],
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream execute agent with given parameters - stateless execution."""
        pass
    
    @abstractmethod
    def validate_configuration(
        self,
        template_id: str,
        template_version: str,
        configuration: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate agent configuration for template."""
        pass
    
    @abstractmethod
    def get_supported_templates(self) -> list[dict[str, Any]]:
        """Get list of supported templates."""
        pass


class FrameworkExecutorInterface(ABC):
    """Abstract interface for framework executors.
    
    This interface defines the core capabilities that any framework executor must provide.
    Framework executors are responsible for managing framework-specific resources and
    providing agent execution capabilities.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Framework name (e.g., 'langgraph', 'crewai', 'autogen')."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Framework version."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Framework description."""
        pass

    @property
    @abstractmethod
    def agent_executor(self) -> AgentExecutorInterface:
        """Get the agent executor for this framework.
        
        Returns:
            Stateless agent executor that can execute agents
        """
        pass

    @abstractmethod
    def get_templates(self) -> list[dict[str, Any]]:
        """Get available templates from this framework.
        
        Returns:
            List of template information dictionaries
        """
        pass

    @abstractmethod
    def get_supported_capabilities(self) -> list[str]:
        """Get list of capabilities supported by this framework.
        
        Returns:
            List of capability names (e.g., 'streaming', 'tools', 'memory')
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the framework executor."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the framework executor."""
        pass

    @abstractmethod
    def get_health_status(self) -> dict[str, Any]:
        """Get framework health status."""
        pass


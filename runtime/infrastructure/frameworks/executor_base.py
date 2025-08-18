"""Pure Framework Executor Interface - No Instance Management."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime, UTC

from ...domain.value_objects.chat_message import ChatMessage
from ...core import BaseService


class ExecutionResult:
    """Result of agent execution."""
    
    def __init__(
        self,
        success: bool,
        message: Optional[str] = None,
        finish_reason: str = "stop",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        processing_time_ms: int = 0,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        context_updated: bool = False
    ):
        self.success = success
        self.message = message
        self.finish_reason = finish_reason
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.processing_time_ms = processing_time_ms
        self.error = error
        self.metadata = metadata or {}
        self.context_updated = context_updated
        self.created_at = datetime.now(UTC)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'message': self.message,
            'finish_reason': self.finish_reason,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'processing_time_ms': self.processing_time_ms,
            'error': self.error,
            'metadata': self.metadata,
            'context_updated': self.context_updated,
            'created_at': self.created_at.isoformat()
        }


class StreamingChunk:
    """Streaming execution chunk."""
    
    def __init__(
        self,
        content: str,
        chunk_index: int = 0,
        finish_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.chunk_index = chunk_index
        self.finish_reason = finish_reason
        self.metadata = metadata or {}
        self.created_at = datetime.now(UTC)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'content': self.content,
            'chunk_index': self.chunk_index,
            'finish_reason': self.finish_reason,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }

class AgentExecutorInterface(ABC):
    """Pure agent executor interface - stateless execution only."""
    
    @abstractmethod
    async def execute(
        self,
        template_id: str,
        template_version: str,
        configuration: Dict[str, Any],
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute agent with given parameters - stateless execution."""
        pass
    
    @abstractmethod
    async def stream_execute(
        self,
        template_id: str,
        template_version: str,
        configuration: Dict[str, Any],
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream execute agent with given parameters - stateless execution."""
        pass
    
    @abstractmethod
    def validate_configuration(
        self,
        template_id: str,
        template_version: str,
        configuration: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """Validate agent configuration for template."""
        pass
    
    @abstractmethod
    def get_supported_templates(self) -> List[Dict[str, Any]]:
        """Get list of supported templates."""
        pass


class FrameworkExecutor(BaseService, ABC):
    """Abstract base class for pure framework executors.
    
    This replaces FrameworkIntegration with a purely stateless execution model.
    No instance management - just pure execution functions.
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

    @abstractmethod
    def create_agent_executor(self) -> AgentExecutorInterface:
        """Create framework-specific agent executor.
        
        Returns:
            Stateless agent executor that can execute agents
        """
        pass

    @abstractmethod
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available templates from this framework.
        
        Returns:
            List of template information dictionaries
        """
        pass

    @abstractmethod
    def get_llm_service(self) -> Any:
        """Get framework-specific LLM service.
        
        Returns:
            LLM service compatible with this framework
        """
        pass

    @abstractmethod
    def get_toolset_service(self) -> Any:
        """Get framework-specific toolset service.
        
        Returns:
            Toolset service compatible with this framework
        """
        pass

    @abstractmethod
    def get_supported_capabilities(self) -> List[str]:
        """Get list of capabilities supported by this framework.
        
        Returns:
            List of capability names (e.g., 'streaming', 'tools', 'memory')
        """
        pass

    def get_health_status(self) -> Dict[str, Any]:
        """Get framework health status."""
        base_status = super().get_health_status()
        base_status.update({
            "framework": self.name,
            "version": self.version,
            "capabilities": self.get_supported_capabilities(),
            "executor_type": "stateless",
            "templates": len(self.get_templates())
        })
        return base_status

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} v{self.version} (Executor)"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"FrameworkExecutor(name='{self.name}', version='{self.version}')"


class ExecutionContext:
    """Context for agent execution - carries state between calls."""
    
    def __init__(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[ChatMessage]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.session_id = session_id
        self.conversation_history = conversation_history or []
        self.metadata = metadata or {}
        self.created_at = datetime.now(UTC)
        self.last_updated = datetime.now(UTC)
        self.execution_count = 0
    
    def update(self, new_messages: List[ChatMessage], response_message: Optional[ChatMessage] = None):
        """Update context with new messages."""
        self.conversation_history.extend(new_messages)
        if response_message:
            self.conversation_history.append(response_message)
        self.last_updated = datetime.now(UTC)
        self.execution_count += 1
        
        # Trim history if too long (configurable)
        max_history = self.metadata.get('max_history_length', 50)
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'agent_id': self.agent_id,
            'session_id': self.session_id,
            'conversation_history': [msg.to_dict() for msg in self.conversation_history],
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'execution_count': self.execution_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """Create from dictionary."""
        context = cls(
            agent_id=data['agent_id'],
            session_id=data.get('session_id'),
            conversation_history=[
                ChatMessage.from_dict(msg_data) 
                for msg_data in data.get('conversation_history', [])
            ],
            metadata=data.get('metadata', {})
        )
        context.created_at = datetime.fromisoformat(data['created_at'])
        context.last_updated = datetime.fromisoformat(data['last_updated'])
        context.execution_count = data.get('execution_count', 0)
        return context

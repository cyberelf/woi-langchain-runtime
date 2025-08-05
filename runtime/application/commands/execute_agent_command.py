"""Execute agent command - Application layer."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from ...domain.value_objects.agent_id import AgentId
from ...domain.value_objects.session_id import SessionId
from ...domain.value_objects.chat_message import ChatMessage


@dataclass(frozen=True)
class ExecuteAgentCommand:
    """Command to execute an agent with a message.
    
    Represents the intent to execute an agent and get a response.
    """
    
    agent_id: AgentId
    messages: List[ChatMessage]
    session_id: Optional[SessionId] = None
    user_id: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate command data."""
        if not self.messages:
            raise ValueError("At least one message is required")
        if not all(isinstance(msg, ChatMessage) for msg in self.messages):
            raise ValueError("All messages must be ChatMessage objects")
        if self.temperature is not None and not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
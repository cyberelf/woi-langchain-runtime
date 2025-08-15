"""Execute agent command - Application layer."""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from ...domain.value_objects.chat_message import ChatMessage


@dataclass(frozen=True)
class ExecuteAgentCommand:
    """Command to execute an agent with a message.
    
    Represents the intent to execute an agent in the system with conversation context.
    """
    
    agent_id: str
    messages: List[ChatMessage]  # Domain value objects
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stream: bool = False
    stop: Optional[List[str]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate command data."""
        if not self.agent_id:
            raise ValueError("Agent ID is required")
        if not self.messages:
            raise ValueError("Messages list cannot be empty")
        if self.temperature is not None and not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
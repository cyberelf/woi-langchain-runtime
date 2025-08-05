"""Chat session entity - Pure domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..value_objects.session_id import SessionId
from ..value_objects.agent_id import AgentId
from ..value_objects.chat_message import ChatMessage


@dataclass
class ChatSession:
    """Chat session entity - Core business logic for chat sessions.
    
    This entity represents a chat conversation session.
    No framework dependencies - pure domain entity.
    """
    
    id: SessionId
    agent_id: AgentId
    user_id: Optional[str]
    conversation_history: List[ChatMessage]
    created_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_history_length: int = 100
    
    def __post_init__(self):
        """Validate session data."""
        if not isinstance(self.conversation_history, list):
            raise ValueError("Conversation history must be a list")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
        if self.max_history_length <= 0:
            raise ValueError("Max history length must be positive")
    
    @classmethod
    def create(
        cls,
        agent_id: AgentId,
        user_id: Optional[str] = None,
        max_history_length: int = 100,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ChatSession":
        """Create a new chat session."""
        now = datetime.utcnow()
        return cls(
            id=SessionId.generate(),
            agent_id=agent_id,
            user_id=user_id,
            conversation_history=[],
            created_at=now,
            last_activity=now,
            metadata=metadata.copy() if metadata else {},
            max_history_length=max_history_length
        )
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the conversation history."""
        if not isinstance(message, ChatMessage):
            raise ValueError("Message must be a ChatMessage")
        
        self.conversation_history.append(message)
        self.last_activity = datetime.utcnow()
        
        # Trim history if it exceeds maximum length
        if len(self.conversation_history) > self.max_history_length:
            # Keep system messages and trim user/assistant messages
            system_messages = [msg for msg in self.conversation_history if msg.is_system_message()]
            other_messages = [msg for msg in self.conversation_history if not msg.is_system_message()]
            
            # Keep the most recent messages up to the limit
            messages_to_keep = self.max_history_length - len(system_messages)
            if messages_to_keep > 0:
                other_messages = other_messages[-messages_to_keep:]
            else:
                other_messages = []
            
            self.conversation_history = system_messages + other_messages
    
    def get_recent_messages(self, count: int) -> List[ChatMessage]:
        """Get the most recent messages."""
        if count <= 0:
            return []
        return self.conversation_history[-count:]
    
    def get_user_messages(self) -> List[ChatMessage]:
        """Get all user messages."""
        return [msg for msg in self.conversation_history if msg.is_user_message()]
    
    def get_assistant_messages(self) -> List[ChatMessage]:
        """Get all assistant messages."""
        return [msg for msg in self.conversation_history if msg.is_assistant_message()]
    
    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.conversation_history)
    
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Check if session is expired based on last activity."""
        if timeout_hours <= 0:
            return False
        
        timeout_delta = timedelta(hours=timeout_hours)
        return datetime.utcnow() - self.last_activity > timeout_delta
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        self.last_activity = datetime.utcnow()
    
    def set_max_history_length(self, length: int) -> None:
        """Set maximum history length."""
        if length <= 0:
            raise ValueError("Max history length must be positive")
        
        self.max_history_length = length
        
        # Trim current history if necessary
        if len(self.conversation_history) > length:
            system_messages = [msg for msg in self.conversation_history if msg.is_system_message()]
            other_messages = [msg for msg in self.conversation_history if not msg.is_system_message()]
            
            messages_to_keep = length - len(system_messages)
            if messages_to_keep > 0:
                other_messages = other_messages[-messages_to_keep:]
            else:
                other_messages = []
            
            self.conversation_history = system_messages + other_messages
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the session."""
        self.metadata[key] = value
        self.touch()
    
    def __eq__(self, other) -> bool:
        """Equality based on ID."""
        if not isinstance(other, ChatSession):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)
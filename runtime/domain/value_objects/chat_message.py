"""Chat message value object - Pure domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class MessageRole(Enum):
    """Message role enumeration."""
    
    SYSTEM = "system"
    USER = "user" 
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ChatMessage:
    """Chat message value object.
    
    Immutable value object representing a chat message.
    No framework dependencies - pure domain concept.
    """
    
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not isinstance(self.role, MessageRole):
            raise ValueError("Role must be a MessageRole enum")
        if not self.content:
            raise ValueError("Message content cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
    
    @classmethod
    def create_user_message(cls, content: str, metadata: Optional[dict[str, Any]] = None) -> "ChatMessage":
        """Create a user message."""
        return cls(
            role=MessageRole.USER,
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
    
    @classmethod
    def create_assistant_message(cls, content: str, metadata: Optional[dict[str, Any]] = None) -> "ChatMessage":
        """Create an assistant message."""
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
    
    @classmethod
    def create_system_message(cls, content: str, metadata: Optional[dict[str, Any]] = None) -> "ChatMessage":
        """Create a system message."""
        return cls(
            role=MessageRole.SYSTEM,
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
    
    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == MessageRole.USER
    
    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == MessageRole.ASSISTANT
    
    def is_system_message(self) -> bool:
        """Check if this is a system message."""
        return self.role == MessageRole.SYSTEM
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        """Create ChatMessage from dictionary representation."""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )
"""Message Queue Interface and Core Types for Agent Task Management."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class MessageStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class QueueMessage:
    """Message in the queue."""
    id: str
    queue_name: str
    payload: dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    delay_seconds: int = 0
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def create(
        cls,
        queue_name: str,
        payload: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> "QueueMessage":
        """Create a new queue message."""
        return cls(
            id=str(uuid.uuid4()),
            queue_name=queue_name,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueMessage":
        """Create message from dictionary."""
        # Convert enum values
        data['priority'] = MessagePriority(data['priority'])
        data['status'] = MessageStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class QueueStats:
    """Queue statistics."""
    queue_name: str
    total_messages: int
    pending_messages: int
    processing_messages: int
    completed_messages: int
    failed_messages: int
    average_processing_time: float
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)


class MessageQueueInterface(ABC):
    """Abstract interface for message queue implementations.
    
    This interface defines the contract for message queue implementations.
    Concrete implementations should be placed in the infrastructure layer.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the message queue."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the message queue."""
        pass
    
    @abstractmethod
    async def send_message(
        self,
        queue_name: str,
        payload: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        delay_seconds: int = 0,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """Send a message to a queue."""
        pass
    
    @abstractmethod
    async def receive_message(
        self,
        queue_name: str,
        timeout_seconds: Optional[int] = None
    ) -> Optional[QueueMessage]:
        """Receive a message from a queue."""
        pass
    
    @abstractmethod
    async def receive_messages(
        self,
        queue_name: str,
        max_messages: int = 10,
        timeout_seconds: Optional[int] = None
    ) -> list[QueueMessage]:
        """Receive multiple messages from a queue."""
        pass
    
    @abstractmethod
    async def acknowledge_message(self, message: QueueMessage) -> bool:
        """Acknowledge message processing completion."""
        pass
    
    @abstractmethod
    async def reject_message(
        self,
        message: QueueMessage,
        requeue: bool = True,
        reason: Optional[str] = None
    ) -> bool:
        """Reject a message and optionally requeue it."""
        pass
    
    @abstractmethod
    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get queue statistics."""
        pass
    
    @abstractmethod
    async def list_queues(self) -> list[str]:
        """List all available queues."""
        pass
    
    @abstractmethod
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue."""
        pass
    
    @abstractmethod
    async def create_queue(
        self,
        queue_name: str,
        max_size: Optional[int] = None,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Create a new queue."""
        pass
    
    @abstractmethod
    async def delete_queue(self, queue_name: str) -> bool:
        """Delete a queue."""
        pass
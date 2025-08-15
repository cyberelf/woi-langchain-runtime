"""Message Queue Interface and Basic Implementation for Agent Task Management."""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
from collections import defaultdict

logger = logging.getLogger(__name__)


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
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    delay_seconds: int = 0
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = None
    
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
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueMessage":
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
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)


class MessageQueueInterface(ABC):
    """Abstract interface for message queue implementations."""
    
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
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        delay_seconds: int = 0,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
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
    ) -> List[QueueMessage]:
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
    async def list_queues(self) -> List[str]:
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


class InMemoryMessageQueue(MessageQueueInterface):
    """In-memory message queue implementation for development and testing."""
    
    def __init__(self):
        self._queues: Dict[str, List[QueueMessage]] = defaultdict(list)
        self._processing: Dict[str, List[QueueMessage]] = defaultdict(list)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._queue_configs: Dict[str, Dict[str, Any]] = {}
        self._stats: Dict[str, QueueStats] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the message queue."""
        if not self._initialized:
            logger.info("Initializing in-memory message queue")
            self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown the message queue."""
        logger.info("Shutting down in-memory message queue")
        async with self._lock:
            self._queues.clear()
            self._processing.clear()
            self._subscribers.clear()
            self._queue_configs.clear()
            self._stats.clear()
        self._initialized = False
    
    async def send_message(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        delay_seconds: int = 0,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send a message to a queue."""
        message = QueueMessage.create(
            queue_name=queue_name,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to,
            metadata=metadata
        )
        message.delay_seconds = delay_seconds
        
        async with self._lock:
            # Insert based on priority (higher priority first)
            queue = self._queues[queue_name]
            inserted = False
            for i, existing in enumerate(queue):
                if message.priority.value > existing.priority.value:
                    queue.insert(i, message)
                    inserted = True
                    break
            
            if not inserted:
                queue.append(message)
            
            # Update stats
            await self._update_queue_stats(queue_name)
        
        logger.debug(f"Sent message {message.id} to queue {queue_name}")
        return message.id
    
    async def receive_message(
        self,
        queue_name: str,
        timeout_seconds: Optional[int] = None
    ) -> Optional[QueueMessage]:
        """Receive a message from a queue."""
        messages = await self.receive_messages(queue_name, max_messages=1, timeout_seconds=timeout_seconds)
        return messages[0] if messages else None
    
    async def receive_messages(
        self,
        queue_name: str,
        max_messages: int = 10,
        timeout_seconds: Optional[int] = None
    ) -> List[QueueMessage]:
        """Receive multiple messages from a queue."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            async with self._lock:
                queue = self._queues[queue_name]
                if not queue:
                    # No messages available
                    if timeout_seconds is None:
                        return []
                    
                    # Check timeout
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= timeout_seconds:
                        return []
                else:
                    # Get messages up to max_messages
                    messages = []
                    for _ in range(min(max_messages, len(queue))):
                        if queue:
                            message = queue.pop(0)
                            message.status = MessageStatus.PROCESSING
                            message.updated_at = datetime.now(timezone.utc)
                            self._processing[queue_name].append(message)
                            messages.append(message)
                    
                    if messages:
                        await self._update_queue_stats(queue_name)
                        logger.debug(f"Received {len(messages)} messages from queue {queue_name}")
                        return messages
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
    
    async def acknowledge_message(self, message: QueueMessage) -> bool:
        """Acknowledge message processing completion."""
        async with self._lock:
            processing_queue = self._processing[message.queue_name]
            for i, msg in enumerate(processing_queue):
                if msg.id == message.id:
                    msg.status = MessageStatus.COMPLETED
                    msg.updated_at = datetime.now(timezone.utc)
                    processing_queue.pop(i)
                    await self._update_queue_stats(message.queue_name)
                    logger.debug(f"Acknowledged message {message.id}")
                    return True
        return False
    
    async def reject_message(
        self,
        message: QueueMessage,
        requeue: bool = True,
        reason: Optional[str] = None
    ) -> bool:
        """Reject a message and optionally requeue it."""
        async with self._lock:
            processing_queue = self._processing[message.queue_name]
            for i, msg in enumerate(processing_queue):
                if msg.id == message.id:
                    processing_queue.pop(i)
                    
                    if requeue and msg.retry_count < msg.max_retries:
                        msg.retry_count += 1
                        msg.status = MessageStatus.RETRY
                        msg.updated_at = datetime.now(timezone.utc)
                        if reason:
                            msg.metadata['reject_reason'] = reason
                        
                        # Requeue with lower priority for retry
                        self._queues[message.queue_name].append(msg)
                        logger.debug(f"Requeued message {message.id} (retry {msg.retry_count}/{msg.max_retries})")
                    else:
                        msg.status = MessageStatus.FAILED
                        msg.updated_at = datetime.now(timezone.utc)
                        if reason:
                            msg.metadata['reject_reason'] = reason
                        logger.warning(f"Failed message {message.id}: {reason}")
                    
                    await self._update_queue_stats(message.queue_name)
                    return True
        return False
    
    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get queue statistics."""
        async with self._lock:
            return self._stats.get(queue_name, QueueStats(
                queue_name=queue_name,
                total_messages=0,
                pending_messages=0,
                processing_messages=0,
                completed_messages=0,
                failed_messages=0,
                average_processing_time=0.0
            ))
    
    async def list_queues(self) -> List[str]:
        """List all available queues."""
        async with self._lock:
            return list(self._queues.keys())
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue."""
        async with self._lock:
            queue = self._queues[queue_name]
            processing = self._processing[queue_name]
            count = len(queue) + len(processing)
            
            queue.clear()
            processing.clear()
            
            await self._update_queue_stats(queue_name)
            logger.info(f"Purged {count} messages from queue {queue_name}")
            return count
    
    async def create_queue(
        self,
        queue_name: str,
        max_size: Optional[int] = None,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Create a new queue."""
        async with self._lock:
            if queue_name not in self._queues:
                self._queues[queue_name] = []
                self._processing[queue_name] = []
                self._queue_configs[queue_name] = {
                    'max_size': max_size,
                    'ttl_seconds': ttl_seconds,
                    'created_at': datetime.now(timezone.utc)
                }
                await self._update_queue_stats(queue_name)
                logger.info(f"Created queue {queue_name}")
                return True
        return False
    
    async def delete_queue(self, queue_name: str) -> bool:
        """Delete a queue."""
        async with self._lock:
            if queue_name in self._queues:
                del self._queues[queue_name]
                del self._processing[queue_name]
                del self._queue_configs[queue_name]
                if queue_name in self._stats:
                    del self._stats[queue_name]
                logger.info(f"Deleted queue {queue_name}")
                return True
        return False
    
    async def _update_queue_stats(self, queue_name: str) -> None:
        """Update queue statistics."""
        queue = self._queues[queue_name]
        processing = self._processing[queue_name]
        
        self._stats[queue_name] = QueueStats(
            queue_name=queue_name,
            total_messages=len(queue) + len(processing),
            pending_messages=len(queue),
            processing_messages=len(processing),
            completed_messages=0,  # Not tracked in in-memory implementation
            failed_messages=0,     # Not tracked in in-memory implementation
            average_processing_time=0.0,  # Not tracked in in-memory implementation
            last_updated=datetime.now(timezone.utc)
        )


class RedisMessageQueue(MessageQueueInterface):
    """Redis-based message queue implementation."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis = None
        
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url)
            await self._redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except ImportError:
            raise ImportError("redis package is required for RedisMessageQueue")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Disconnected from Redis")
    
    # Implementation would continue with Redis-specific operations...
    # For brevity, showing structure only
    
    async def send_message(self, queue_name: str, payload: Dict[str, Any], **kwargs) -> str:
        """Send message to Redis queue."""
        # Implementation using Redis lists/streams
        raise NotImplementedError("Redis implementation to be completed")
    
    # ... other methods would be implemented with Redis operations


class RabbitMQMessageQueue(MessageQueueInterface):
    """RabbitMQ-based message queue implementation."""
    
    def __init__(self, amqp_url: str = "amqp://localhost:5672"):
        self.amqp_url = amqp_url
        self._connection = None
        self._channel = None
        
    async def initialize(self) -> None:
        """Initialize RabbitMQ connection."""
        try:
            import aio_pika
            self._connection = await aio_pika.connect_robust(self.amqp_url)
            self._channel = await self._connection.channel()
            logger.info(f"Connected to RabbitMQ at {self.amqp_url}")
        except ImportError:
            raise ImportError("aio-pika package is required for RabbitMQMessageQueue")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to RabbitMQ: {e}")
    
    # ... implementation would continue with RabbitMQ operations
    
    async def send_message(self, queue_name: str, payload: Dict[str, Any], **kwargs) -> str:
        """Send message to RabbitMQ queue."""
        # Implementation using aio_pika
        raise NotImplementedError("RabbitMQ implementation to be completed")


def create_message_queue(queue_type: str = "memory", **kwargs) -> MessageQueueInterface:
    """Factory function to create message queue implementations."""
    if queue_type == "memory":
        return InMemoryMessageQueue()
    elif queue_type == "redis":
        return RedisMessageQueue(kwargs.get("redis_url", "redis://localhost:6379"))
    elif queue_type == "rabbitmq":
        return RabbitMQMessageQueue(kwargs.get("amqp_url", "amqp://localhost:5672"))
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")
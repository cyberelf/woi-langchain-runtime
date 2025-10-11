"""In-memory message queue implementation for development and testing."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict

from ...core.message_queue import (
    MessageQueueInterface,
    QueueMessage,
    MessagePriority,
    MessageStatus,
    QueueStats
)

logger = logging.getLogger(__name__)


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
                if queue_name in self._queue_configs:
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

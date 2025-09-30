"""Unit tests for InMemoryMessageQueue implementation."""

import asyncio
import pytest
import pytest_asyncio

from runtime.infrastructure.message_queues.in_memory import InMemoryMessageQueue
from runtime.core.message_queue import (
    QueueMessage,
    MessagePriority,
    MessageStatus,
)


class TestInMemoryMessageQueue:
    """Test the InMemoryMessageQueue implementation."""

    @pytest_asyncio.fixture
    async def queue(self):
        """Create and initialize a message queue instance."""
        queue = InMemoryMessageQueue()
        await queue.initialize()
        yield queue
        await queue.shutdown()

    @pytest.fixture
    def sample_payload(self):
        """Create sample message payload."""
        return {"action": "test", "data": {"key": "value"}}

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test queue initialization and shutdown."""
        queue = InMemoryMessageQueue()
        
        # Should not be initialized initially
        assert not queue._initialized
        
        # Initialize
        await queue.initialize()
        assert queue._initialized
        
        # Should be idempotent
        await queue.initialize()
        assert queue._initialized
        
        # Shutdown
        await queue.shutdown()
        assert not queue._initialized

    @pytest.mark.asyncio
    async def test_send_message_basic(self, queue, sample_payload):
        """Test basic message sending."""
        message_id = await queue.send_message("test-queue", sample_payload)
        
        # Should return a message ID
        assert message_id is not None
        assert isinstance(message_id, str)
        
        # Queue should have the message
        stats = await queue.get_queue_stats("test-queue")
        assert stats.pending_messages == 1
        assert stats.total_messages == 1

    @pytest.mark.asyncio
    async def test_send_message_with_all_parameters(self, queue, sample_payload):
        """Test sending message with all optional parameters."""
        message_id = await queue.send_message(
            queue_name="test-queue",
            payload=sample_payload,
            priority=MessagePriority.HIGH,
            delay_seconds=5,
            correlation_id="corr-123",
            reply_to="reply-queue",
            metadata={"source": "test"}
        )
        
        assert message_id is not None
        
        # Verify message was queued
        stats = await queue.get_queue_stats("test-queue")
        assert stats.pending_messages == 1

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue, sample_payload):
        """Test that messages are ordered by priority."""
        # Send messages with different priorities
        normal_id = await queue.send_message("test-queue", {"type": "normal"}, MessagePriority.NORMAL)
        high_id = await queue.send_message("test-queue", {"type": "high"}, MessagePriority.HIGH)
        low_id = await queue.send_message("test-queue", {"type": "low"}, MessagePriority.LOW)
        urgent_id = await queue.send_message("test-queue", {"type": "urgent"}, MessagePriority.URGENT)
        
        # Receive messages - should come in priority order
        messages = await queue.receive_messages("test-queue", max_messages=4)
        
        assert len(messages) == 4
        assert messages[0].payload["type"] == "urgent"  # Highest priority first
        assert messages[1].payload["type"] == "high"
        assert messages[2].payload["type"] == "normal"
        assert messages[3].payload["type"] == "low"     # Lowest priority last

    @pytest.mark.asyncio
    async def test_receive_single_message(self, queue, sample_payload):
        """Test receiving a single message."""
        # Send a message
        await queue.send_message("test-queue", sample_payload)
        
        # Receive it
        message = await queue.receive_message("test-queue")
        
        assert message is not None
        assert message.payload == sample_payload
        assert message.status == MessageStatus.PROCESSING
        assert message.queue_name == "test-queue"

    @pytest.mark.asyncio
    async def test_receive_multiple_messages(self, queue, sample_payload):
        """Test receiving multiple messages."""
        # Send multiple messages
        for i in range(5):
            await queue.send_message("test-queue", {"index": i})
        
        # Receive up to 3 messages
        messages = await queue.receive_messages("test-queue", max_messages=3)
        
        assert len(messages) == 3
        for i, message in enumerate(messages):
            assert message.payload["index"] == i
            assert message.status == MessageStatus.PROCESSING
        
        # Should have 2 messages left in queue
        stats = await queue.get_queue_stats("test-queue")
        assert stats.pending_messages == 2
        assert stats.processing_messages == 3

    @pytest.mark.asyncio
    async def test_receive_from_empty_queue(self, queue):
        """Test receiving from empty queue without timeout."""
        messages = await queue.receive_messages("empty-queue", max_messages=1)
        assert messages == []
        
        message = await queue.receive_message("empty-queue")
        assert message is None

    @pytest.mark.asyncio
    async def test_receive_with_timeout(self, queue):
        """Test receiving with timeout on empty queue."""
        start_time = asyncio.get_event_loop().time()
        
        # Should timeout after 1 second
        messages = await queue.receive_messages("empty-queue", timeout_seconds=1)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        assert messages == []
        assert 0.9 <= elapsed <= 1.5  # Allow some variance for timing

    @pytest.mark.asyncio
    async def test_receive_with_timeout_success(self, queue, sample_payload):
        """Test receiving with timeout when message becomes available."""
        async def delayed_send():
            await asyncio.sleep(0.2)  # Send after 200ms
            await queue.send_message("test-queue", sample_payload)
        
        # Start delayed send
        asyncio.create_task(delayed_send())
        
        # Should receive the message before timeout
        messages = await queue.receive_messages("test-queue", timeout_seconds=1)
        
        assert len(messages) == 1
        assert messages[0].payload == sample_payload

    @pytest.mark.asyncio
    async def test_acknowledge_message(self, queue, sample_payload):
        """Test message acknowledgement."""
        # Send and receive message
        await queue.send_message("test-queue", sample_payload)
        message = await queue.receive_message("test-queue")
        
        assert message.status == MessageStatus.PROCESSING
        
        # Acknowledge the message
        ack_result = await queue.acknowledge_message(message)
        assert ack_result is True
        
        # Message should be removed from processing queue
        stats = await queue.get_queue_stats("test-queue")
        assert stats.processing_messages == 0
        assert stats.pending_messages == 0

    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_message(self, queue):
        """Test acknowledging a message that doesn't exist."""
        fake_message = QueueMessage.create("test-queue", {"fake": "message"})
        
        ack_result = await queue.acknowledge_message(fake_message)
        assert ack_result is False

    @pytest.mark.asyncio 
    async def test_queue_cleanup_on_shutdown(self, queue):
        """Test that queue properly cleans up on shutdown."""
        # Add some state
        await queue.send_message("cleanup-queue", {"test": "data"})
        message = await queue.receive_message("cleanup-queue")
        
        # Verify state exists
        stats = await queue.get_queue_stats("cleanup-queue")
        assert stats.processing_messages == 1
        
        # Shutdown
        await queue.shutdown()
        
        # State should be cleaned up
        assert len(queue._queues) == 0
        assert len(queue._processing) == 0
        assert len(queue._stats) == 0
        assert not queue._initialized

    @pytest.mark.asyncio
    async def test_message_priority_with_task_ids(self, queue):
        """Test priority ordering with task identifiers."""
        # Send messages with different priorities
        messages = [
            (MessagePriority.LOW, "low-priority-task"),
            (MessagePriority.HIGH, "high-priority-task"), 
            (MessagePriority.NORMAL, "normal-priority-task"),
            (MessagePriority.URGENT, "urgent-priority-task")
        ]
        
        for priority, task_id in messages:
            await queue.send_message("priority-queue", {"task_id": task_id}, priority=priority)
        
        # Receive messages - should come in priority order
        received_order = []
        for _ in range(4):
            message = await queue.receive_message("priority-queue")
            received_order.append(message.payload["task_id"])
            await queue.acknowledge_message(message)
        
        # Should be in priority order
        expected_order = ["urgent-priority-task", "high-priority-task", "normal-priority-task", "low-priority-task"]
        assert received_order == expected_order

    @pytest.mark.asyncio
    async def test_reject_message_with_requeue(self, queue, sample_payload):
        """Test rejecting a message with requeue."""
        # Send and receive message
        await queue.send_message("test-queue", sample_payload)
        message = await queue.receive_message("test-queue")
        
        # Reject with requeue
        reject_result = await queue.reject_message(message, requeue=True, reason="Test rejection")
        assert reject_result is True
        
        # Message should be back in queue with retry status
        stats = await queue.get_queue_stats("test-queue")
        assert stats.pending_messages == 1
        assert stats.processing_messages == 0
        
        # Receive again and check retry count
        retried_message = await queue.receive_message("test-queue")
        assert retried_message.retry_count == 1
        assert retried_message.metadata.get("reject_reason") == "Test rejection"

    @pytest.mark.asyncio
    async def test_reject_message_without_requeue(self, queue, sample_payload):
        """Test rejecting a message without requeue."""
        # Send and receive message
        await queue.send_message("test-queue", sample_payload)
        message = await queue.receive_message("test-queue")
        
        # Reject without requeue
        reject_result = await queue.reject_message(message, requeue=False, reason="Permanent failure")
        assert reject_result is True
        
        # Message should not be in queue anymore
        stats = await queue.get_queue_stats("test-queue")
        assert stats.pending_messages == 0
        assert stats.processing_messages == 0

    @pytest.mark.asyncio
    async def test_reject_message_max_retries_exceeded(self, queue, sample_payload):
        """Test rejecting message when max retries exceeded."""
        # Send and receive message
        await queue.send_message("test-queue", sample_payload)
        message = await queue.receive_message("test-queue")
        
        # Set retry count to max
        message.retry_count = message.max_retries
        
        # Reject with requeue - should fail permanently
        reject_result = await queue.reject_message(message, requeue=True)
        assert reject_result is True
        
        # Message should not be requeued
        stats = await queue.get_queue_stats("test-queue")
        assert stats.pending_messages == 0
        assert stats.processing_messages == 0

    @pytest.mark.asyncio
    async def test_queue_stats(self, queue, sample_payload):
        """Test queue statistics accuracy."""
        queue_name = "stats-test-queue"
        
        # Send messages
        for i in range(3):
            await queue.send_message(queue_name, {"index": i})
        
        stats = await queue.get_queue_stats(queue_name)
        assert stats.queue_name == queue_name
        assert stats.pending_messages == 3
        assert stats.processing_messages == 0
        assert stats.total_messages == 3
        
        # Receive one message
        message = await queue.receive_message(queue_name)
        
        stats = await queue.get_queue_stats(queue_name)
        assert stats.pending_messages == 2
        assert stats.processing_messages == 1
        assert stats.total_messages == 3
        
        # Acknowledge the message
        await queue.acknowledge_message(message)
        
        stats = await queue.get_queue_stats(queue_name)
        assert stats.pending_messages == 2
        assert stats.processing_messages == 0
        assert stats.total_messages == 2

    @pytest.mark.asyncio
    async def test_queue_stats_nonexistent_queue(self, queue):
        """Test getting stats for non-existent queue."""
        stats = await queue.get_queue_stats("non-existent-queue")
        
        assert stats.queue_name == "non-existent-queue"
        assert stats.total_messages == 0
        assert stats.pending_messages == 0
        assert stats.processing_messages == 0

    @pytest.mark.asyncio
    async def test_list_queues(self, queue):
        """Test listing all queues."""
        # Initially no queues
        queues = await queue.list_queues()
        assert queues == []
        
        # Send messages to different queues
        await queue.send_message("queue1", {"test": 1})
        await queue.send_message("queue2", {"test": 2})
        await queue.send_message("queue1", {"test": 3})  # Same queue again
        
        queues = await queue.list_queues()
        assert set(queues) == {"queue1", "queue2"}

    @pytest.mark.asyncio
    async def test_create_queue(self, queue):
        """Test explicit queue creation."""
        result = await queue.create_queue("explicit-queue", max_size=100, ttl_seconds=3600)
        assert result is True
        
        # Queue should appear in list
        queues = await queue.list_queues()
        assert "explicit-queue" in queues
        
        # Creating same queue again should return False
        result = await queue.create_queue("explicit-queue")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_queue(self, queue, sample_payload):
        """Test queue deletion."""
        # Create queue with messages
        await queue.send_message("delete-test-queue", sample_payload)
        await queue.send_message("delete-test-queue", sample_payload)
        
        # Verify queue exists
        queues = await queue.list_queues()
        assert "delete-test-queue" in queues
        
        # Delete queue
        result = await queue.delete_queue("delete-test-queue")
        assert result is True
        
        # Queue should be gone
        queues = await queue.list_queues()
        assert "delete-test-queue" not in queues
        
        # Deleting non-existent queue should return False
        result = await queue.delete_queue("non-existent-queue")
        assert result is False

    @pytest.mark.asyncio
    async def test_purge_queue(self, queue, sample_payload):
        """Test purging all messages from queue."""
        # Add messages in different states
        await queue.send_message("purge-test-queue", sample_payload)
        await queue.send_message("purge-test-queue", sample_payload)
        
        # Receive one message (moves to processing)
        message = await queue.receive_message("purge-test-queue")
        
        stats = await queue.get_queue_stats("purge-test-queue")
        assert stats.pending_messages == 1
        assert stats.processing_messages == 1
        
        # Purge queue
        purged_count = await queue.purge_queue("purge-test-queue")
        assert purged_count == 2
        
        # Queue should be empty
        stats = await queue.get_queue_stats("purge-test-queue")
        assert stats.pending_messages == 0
        assert stats.processing_messages == 0
        assert stats.total_messages == 0

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, queue):
        """Test concurrent sending and receiving operations."""
        async def sender():
            for i in range(10):
                await queue.send_message("concurrent-queue", {"index": i})
                await asyncio.sleep(0.01)  # Small delay
        
        async def receiver():
            received_messages = []
            for _ in range(10):
                while True:
                    message = await queue.receive_message("concurrent-queue", timeout_seconds=1)
                    if message:
                        received_messages.append(message)
                        await queue.acknowledge_message(message)
                        break
                    await asyncio.sleep(0.01)
            return received_messages
        
        # Run sender and receiver concurrently
        sender_task = asyncio.create_task(sender())
        receiver_task = asyncio.create_task(receiver())
        
        await sender_task
        received_messages = await receiver_task
        
        # All messages should be received
        assert len(received_messages) == 10
        
        # Queue should be empty
        stats = await queue.get_queue_stats("concurrent-queue")
        assert stats.total_messages == 0

    @pytest.mark.asyncio
    async def test_message_status_transitions(self, queue, sample_payload):
        """Test message status transitions through lifecycle."""
        # Send message
        message_id = await queue.send_message("lifecycle-queue", sample_payload)
        
        # Check initial status (by getting stats)
        stats = await queue.get_queue_stats("lifecycle-queue")
        assert stats.pending_messages == 1
        
        # Receive message - status should change to PROCESSING
        message = await queue.receive_message("lifecycle-queue")
        assert message.status == MessageStatus.PROCESSING
        
        stats = await queue.get_queue_stats("lifecycle-queue")
        assert stats.pending_messages == 0
        assert stats.processing_messages == 1
        
        # Acknowledge message - should be completed and removed
        await queue.acknowledge_message(message)
        
        stats = await queue.get_queue_stats("lifecycle-queue")
        assert stats.processing_messages == 0

    @pytest.mark.asyncio
    async def test_delay_seconds_parameter(self, queue, sample_payload):
        """Test delay_seconds parameter (stored but not implemented in in-memory)."""
        # Send message with delay - should still be immediately available in in-memory implementation
        await queue.send_message("delay-queue", sample_payload, delay_seconds=60)
        
        # Message should be immediately available (in-memory doesn't implement delays)
        message = await queue.receive_message("delay-queue", timeout_seconds=1)
        assert message is not None
        assert message.delay_seconds == 60

    @pytest.mark.asyncio
    async def test_correlation_id_and_reply_to(self, queue, sample_payload):
        """Test correlation_id and reply_to fields."""
        correlation_id = "test-correlation-123"
        reply_to = "reply-queue"
        
        await queue.send_message(
            "test-queue",
            sample_payload,
            correlation_id=correlation_id,
            reply_to=reply_to
        )
        
        message = await queue.receive_message("test-queue")
        assert message.correlation_id == correlation_id
        assert message.reply_to == reply_to

    @pytest.mark.asyncio
    async def test_metadata_preservation(self, queue, sample_payload):
        """Test that metadata is preserved through message lifecycle."""
        metadata = {"source": "test", "version": "1.0", "flags": {"debug": True}}
        
        await queue.send_message("metadata-queue", sample_payload, metadata=metadata)
        
        message = await queue.receive_message("metadata-queue")
        assert message.metadata == metadata
        
        # Reject message with reason - should add to metadata
        await queue.reject_message(message, requeue=True, reason="Test reason")
        
        retried_message = await queue.receive_message("metadata-queue")
        assert retried_message.metadata["source"] == "test"  # Original metadata preserved
        assert retried_message.metadata["reject_reason"] == "Test reason"  # New metadata added

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, queue, sample_payload):
        """Test that shutdown properly cleans up resources."""
        # Add some messages and state
        await queue.send_message("cleanup-queue", sample_payload)
        message = await queue.receive_message("cleanup-queue")
        await queue.create_queue("explicit-queue")
        
        # Verify state exists
        assert len(queue._queues) > 0
        assert len(queue._processing) > 0
        
        # Shutdown should clean everything
        await queue.shutdown()
        
        assert len(queue._queues) == 0
        assert len(queue._processing) == 0
        assert len(queue._subscribers) == 0
        assert len(queue._queue_configs) == 0
        assert len(queue._stats) == 0
        assert not queue._initialized

    @pytest.mark.asyncio
    async def test_queue_message_serialization(self):
        """Test QueueMessage to_dict and from_dict methods."""
        original_message = QueueMessage.create(
            queue_name="test-queue",
            payload={"test": "data"},
            priority=MessagePriority.HIGH,
            correlation_id="corr-123",
            reply_to="reply-queue",
            metadata={"source": "test"}
        )
        
        # Serialize to dict
        message_dict = original_message.to_dict()
        
        # Should contain all fields
        assert message_dict["queue_name"] == "test-queue"
        assert message_dict["payload"] == {"test": "data"}
        assert message_dict["priority"] == MessagePriority.HIGH.value
        assert message_dict["correlation_id"] == "corr-123"
        assert message_dict["reply_to"] == "reply-queue"
        assert message_dict["metadata"] == {"source": "test"}
        
        # Deserialize from dict
        restored_message = QueueMessage.from_dict(message_dict)
        
        # Should be equivalent
        assert restored_message.id == original_message.id
        assert restored_message.queue_name == original_message.queue_name
        assert restored_message.payload == original_message.payload
        assert restored_message.priority == original_message.priority
        assert restored_message.correlation_id == original_message.correlation_id
        assert restored_message.reply_to == original_message.reply_to
        assert restored_message.metadata == original_message.metadata

    @pytest.mark.asyncio
    async def test_edge_case_empty_payload(self, queue):
        """Test sending message with empty payload."""
        await queue.send_message("empty-payload-queue", {})
        
        message = await queue.receive_message("empty-payload-queue")
        assert message is not None
        assert message.payload == {}

    @pytest.mark.asyncio
    async def test_edge_case_large_payload(self, queue):
        """Test sending message with large payload."""
        large_payload = {"data": "x" * 10000}  # 10KB of data
        
        await queue.send_message("large-payload-queue", large_payload)
        
        message = await queue.receive_message("large-payload-queue")
        assert message is not None
        assert message.payload == large_payload

    @pytest.mark.asyncio
    async def test_multiple_queues_isolation(self, queue):
        """Test that multiple queues don't interfere with each other."""
        # Send messages to different queues
        await queue.send_message("queue-a", {"queue": "A", "message": 1})
        await queue.send_message("queue-b", {"queue": "B", "message": 1})
        await queue.send_message("queue-a", {"queue": "A", "message": 2})
        
        # Receive from queue-a
        message_a1 = await queue.receive_message("queue-a")
        assert message_a1.payload["queue"] == "A"
        assert message_a1.payload["message"] == 1
        
        # Queue-b should still have its message
        stats_b = await queue.get_queue_stats("queue-b")
        assert stats_b.pending_messages == 1
        
        # Receive from queue-b
        message_b1 = await queue.receive_message("queue-b")
        assert message_b1.payload["queue"] == "B"
        assert message_b1.payload["message"] == 1
        
        # Queue-a should still have one message
        message_a2 = await queue.receive_message("queue-a")
        assert message_a2.payload["queue"] == "A"
        assert message_a2.payload["message"] == 2

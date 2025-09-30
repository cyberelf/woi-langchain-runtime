"""Integration tests for InMemoryMessageQueue with AgentOrchestrator patterns."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from runtime.infrastructure.message_queues.in_memory import InMemoryMessageQueue
from runtime.core.message_queue import (
    QueueMessage,
    MessagePriority,
    MessageStatus
)
from runtime.core.agent_orchestrator import (
    AgentMessageRequest,
    MessageType,
    AgentOrchestrator
)
from runtime.domain.value_objects.chat_message import ChatMessage


class TestInMemoryMessageQueueIntegration:
    """Test InMemoryMessageQueue integration with real usage patterns."""

    @pytest.fixture
    async def queue(self):
        """Create and initialize a message queue."""
        queue = InMemoryMessageQueue()
        await queue.initialize()
        yield queue
        await queue.shutdown()

    @pytest.fixture
    def mock_uow(self):
        """Mock unit of work."""
        return AsyncMock()

    @pytest.fixture
    def mock_framework_executor(self):
        """Mock framework executor."""
        return AsyncMock()

    @pytest.fixture
    async def orchestrator(self, queue, mock_uow, mock_framework_executor):
        """Create orchestrator with real message queue."""
        orch = AgentOrchestrator(
            message_queue=queue,
            uow=mock_uow,
            framework_executor=mock_framework_executor,
            max_workers=2
        )
        await orch.initialize()
        yield orch
        await orch.shutdown()

    @pytest.fixture
    def sample_message_request(self):
        """Create sample agent message request."""
        messages = [ChatMessage.create_user_message("Test message")]
        return AgentMessageRequest.create_execute_message(
            agent_id="test-agent-123",
            messages=messages,
            task_id="test-task-456",
            user_id="test-user"
        )

    @pytest.mark.asyncio
    async def test_acknowledge_after_processing_error(self, queue, sample_message_request):
        """Test message acknowledgment after processing errors."""
        # Send message
        message_dict = sample_message_request.to_dict()
        await queue.send_message("test-queue", message_dict)
        
        # Receive message
        queue_message = await queue.receive_message("test-queue")
        assert queue_message.status == MessageStatus.PROCESSING
        
        # Simulate error during processing (but message should still be acknowledged)
        try:
            raise RuntimeError("Simulated processing error")
        except Exception:
            # Even with error, message should be acknowledgeable
            ack_result = await queue.acknowledge_message(queue_message)
            assert ack_result is True
        
        # Verify message is no longer in processing
        stats = await queue.get_queue_stats("test-queue")
        assert stats.processing_messages == 0

    @pytest.mark.asyncio
    async def test_reject_with_requeue_pattern(self, queue, sample_message_request):
        """Test the reject/requeue pattern used by orchestrator."""
        # Send message
        message_dict = sample_message_request.to_dict()
        await queue.send_message("test-queue", message_dict)
        
        # Receive message
        queue_message = await queue.receive_message("test-queue")
        
        # Reject without requeue (as orchestrator does on permanent failure)
        reject_result = await queue.reject_message(
            queue_message, 
            requeue=False, 
            reason="Agent execution failed"
        )
        assert reject_result is True
        
        # Message should not be requeued
        stats = await queue.get_queue_stats("test-queue")
        assert stats.pending_messages == 0
        assert stats.processing_messages == 0

    @pytest.mark.asyncio
    async def test_multiple_workers_same_queue(self, queue):
        """Test multiple workers processing from same queue (as in orchestrator)."""
        # Send multiple messages
        for i in range(10):
            message_req = AgentMessageRequest.create_execute_message(
                agent_id=f"agent-{i}",
                messages=[ChatMessage.create_user_message(f"Message {i}")]
            )
            await queue.send_message("worker-test-queue", message_req.to_dict())
        
        # Simulate multiple workers
        results = []
        
        async def worker(worker_id):
            worker_results = []
            while True:
                message = await queue.receive_message("worker-test-queue", timeout_seconds=1)
                if not message:
                    break
                
                # Simulate processing
                request = AgentMessageRequest.from_dict(message.payload)
                worker_results.append(f"worker-{worker_id}-processed-{request.agent_id}")
                
                # Acknowledge
                await queue.acknowledge_message(message)
                
            return worker_results
        
        # Run 3 workers concurrently
        worker_tasks = [worker(i) for i in range(3)]
        worker_results = await asyncio.gather(*worker_tasks)
        
        # Flatten results
        all_results = []
        for worker_result in worker_results:
            all_results.extend(worker_result)
        
        # Should have processed all 10 messages
        assert len(all_results) == 10
        
        # Each message should be processed exactly once
        agent_ids = [result.split('-processed-')[1] for result in all_results]
        expected_agent_ids = [f"agent-{i}" for i in range(10)]
        assert sorted(agent_ids) == sorted(expected_agent_ids)



    @pytest.mark.asyncio
    async def test_concurrent_queue_stats_updates(self, queue):
        """Test that queue stats remain consistent under concurrent operations."""
        queue_name = "concurrent-stats-queue"
        
        async def sender():
            for i in range(20):
                message_req = AgentMessageRequest.create_execute_message(
                    agent_id=f"sender-agent-{i}",
                    messages=[ChatMessage.create_user_message(f"Message {i}")]
                )
                await queue.send_message(queue_name, message_req.to_dict())
                await asyncio.sleep(0.001)  # Small delay to create interleaving
        
        async def receiver():
            processed = 0
            while processed < 20:
                message = await queue.receive_message(queue_name, timeout_seconds=5)
                if message:
                    await queue.acknowledge_message(message)
                    processed += 1
                await asyncio.sleep(0.001)
            return processed
        
        # Start both operations concurrently
        sender_task = asyncio.create_task(sender())
        receiver_task = asyncio.create_task(receiver())
        
        # Wait for both to complete
        await sender_task
        processed_count = await receiver_task
        
        # Verify final state is consistent
        assert processed_count == 20
        
        final_stats = await queue.get_queue_stats(queue_name)
        assert final_stats.pending_messages == 0
        assert final_stats.processing_messages == 0
        assert final_stats.total_messages == 0

    @pytest.mark.asyncio
    async def test_large_message_handling(self, queue):
        """Test handling of large messages that might occur in real usage."""
        # Create a large message (simulating large conversation history)
        large_messages = []
        for i in range(100):  # 100 chat messages
            large_messages.append(ChatMessage.create_user_message(f"Message {i}: " + "x" * 1000))
        
        large_request = AgentMessageRequest.create_execute_message(
            agent_id="large-message-agent",
            messages=large_messages,
            task_id="large-conversation-task",
            metadata={"conversation_size": len(large_messages)}
        )
        
        # Send and receive large message
        await queue.send_message("large-message-queue", large_request.to_dict())
        
        received_message = await queue.receive_message("large-message-queue")
        restored_request = AgentMessageRequest.from_dict(received_message.payload)
        
        # Verify large message integrity
        assert len(restored_request.messages) == 100
        assert restored_request.task_id == "large-conversation-task"
        assert restored_request.metadata["conversation_size"] == 100
        
        # Clean up
        await queue.acknowledge_message(received_message)

    @pytest.mark.asyncio
    async def test_error_during_message_processing(self, queue):
        """Test error handling patterns used by orchestrator."""
        # Send a message
        message_req = AgentMessageRequest.create_execute_message(
            agent_id="error-test-agent",
            messages=[ChatMessage.create_user_message("This will cause error")]
        )
        await queue.send_message("error-queue", message_req.to_dict())
        
        # Receive message
        queue_message = await queue.receive_message("error-queue")
        
        try:
            # Simulate the kind of error that might occur in orchestrator
            raise RuntimeError("Agent execution failed: Model timeout")
        except Exception as e:
            # Follow the error handling pattern from orchestrator
            error_reason = str(e)
            
            # Reject message without requeue (permanent failure)
            reject_result = await queue.reject_message(
                queue_message, 
                requeue=False, 
                reason=error_reason
            )
            assert reject_result is True
        
        # Verify message is not requeued
        empty_receive = await queue.receive_message("error-queue", timeout_seconds=1)
        assert empty_receive is None
        
        # Stats should show no pending or processing messages
        stats = await queue.get_queue_stats("error-queue")
        assert stats.pending_messages == 0
        assert stats.processing_messages == 0

    @pytest.mark.asyncio
    async def test_queue_isolation(self, queue):
        """Test that different queue types don't interfere (MESSAGE_QUEUE vs RESULT_QUEUE)."""
        # Simulate orchestrator's queue usage pattern
        MESSAGE_QUEUE = "agent.messages"
        RESULT_QUEUE = "agent.results"
        
        # Send to message queue
        message_req = AgentMessageRequest.create_execute_message(
            agent_id="isolation-test-agent",
            messages=[ChatMessage.create_user_message("Test")]
        )
        await queue.send_message(MESSAGE_QUEUE, message_req.to_dict())
        
        # Send to result queue
        result_data = {"result": "test", "success": True}
        await queue.send_message(RESULT_QUEUE, result_data)
        
        # Receive from each queue
        message_received = await queue.receive_message(MESSAGE_QUEUE)
        result_received = await queue.receive_message(RESULT_QUEUE)
        
        # Verify isolation
        assert message_received is not None
        assert result_received is not None
        assert "agent_id" in message_received.payload  # Message queue content
        assert "result" in result_received.payload     # Result queue content
        
        # Clean up
        await queue.acknowledge_message(message_received)
        await queue.acknowledge_message(result_received)

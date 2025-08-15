"""Tests for the new async task management architecture."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# anext is a built-in function in Python 3.10+
from runtime.core.message_queue import InMemoryMessageQueue, MessagePriority
from runtime.core.agent_task_manager import AgentTaskManager, AgentTaskRequest, TaskType
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.domain.entities.agent import Agent
from runtime.domain.value_objects.agent_id import AgentId


class MockUnitOfWork:
    """Mock unit of work for testing."""
    
    def __init__(self):
        self.agents = MagicMock()
        self._in_transaction = False
    
    async def __aenter__(self):
        self._in_transaction = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._in_transaction = False


class MockFrameworkExecutor:
    """Mock framework executor for testing."""
    
    def __init__(self):
        self.name = "mock_framework"
        self.version = "1.0.0"
    
    async def initialize(self):
        pass
    
    def create_agent_factory(self):
        return MockAgentFactory()


class MockAgentFactory:
    """Mock agent factory for testing."""
    
    def __init__(self):
        self.agents = {}
    
    def create_agent(self, agent_request):
        mock_agent = MockAgentInstance(agent_request.id)
        self.agents[agent_request.id] = mock_agent
        return mock_agent
    
    def get_agent(self, agent_id):
        return self.agents.get(agent_id)
    
    def destroy_agent(self, agent_id):
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    def list_agents(self):
        return list(self.agents.keys())


class MockAgentInstance:
    """Mock agent instance for testing."""
    
    def __init__(self, agent_id):
        self.agent_id = agent_id
    
    async def execute(self, messages, temperature=0.7, max_tokens=None, metadata=None):
        # Mock response
        return MockResponse(f"Mock response for {self.agent_id}")
    
    async def stream_execute(self, messages, temperature=0.7, max_tokens=None, metadata=None):
        # Mock streaming
        chunks = ["Hello", " from", " mock", " agent"]
        for i, chunk in enumerate(chunks):
            yield MockChunk(chunk, i == len(chunks) - 1)


class MockResponse:
    """Mock LLM response."""
    
    def __init__(self, content):
        self.choices = [MockChoice(content)]
        self.usage = MockUsage()


class MockChoice:
    """Mock choice in response."""
    
    def __init__(self, content):
        self.message = MockMessage(content)
        self.finish_reason = "stop"


class MockMessage:
    """Mock message."""
    
    def __init__(self, content):
        self.content = content


class MockUsage:
    """Mock usage statistics."""
    
    def __init__(self):
        self.prompt_tokens = 10
        self.completion_tokens = 20


class MockChunk:
    """Mock streaming chunk."""
    
    def __init__(self, content, is_last=False):
        self.content = content
        self.finish_reason = "stop" if is_last else None


@pytest.fixture
async def task_manager():
    """Create task manager for testing."""
    message_queue = InMemoryMessageQueue()
    uow = MockUnitOfWork()
    
    # Create mock agent for UoW
    mock_agent = Agent.create(
        name="Test Agent",
        template_id="test-template",
        template_version="1.0.0",
        configuration={"test": "config"},
        metadata={"test": "metadata"}
    )
    uow.agents.get_by_id = AsyncMock(return_value=mock_agent)
    
    task_manager = AgentTaskManager(
        message_queue=message_queue,
        uow=uow,
        max_workers=2,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )
    
    # Initialize with mock framework
    mock_framework = MockFrameworkExecutor()
    await task_manager.initialize(mock_framework)
    
    yield task_manager
    
    # Cleanup
    await task_manager.shutdown()


@pytest.mark.asyncio
async def test_task_submission_and_execution(task_manager):
    """Test basic task submission and execution."""
    tm = await anext(task_manager)
    # Create task request
    messages = [ChatMessage.create_user_message("Hello, test agent!")]
    task_request = AgentTaskRequest.create_execute_task(
        agent_id="test-agent-123",
        messages=messages,
        session_id="test-session",
        user_id="test-user"
    )
    
    # Submit task
    task_id = await tm.submit_task(task_request)
    assert task_id == task_request.task_id
    
    # Wait for result
    result = await tm.get_task_result(task_id, timeout_seconds=10)
    
    # Verify result
    assert result is not None
    assert result.task_id == task_id
    assert result.agent_id == "test-agent-123"
    assert result.message == "Mock response for test-agent-123#test-session"


@pytest.mark.asyncio
async def test_session_agent_reuse(task_manager):
    """Test that session agents are reused across multiple executions."""
    tm = await anext(task_manager)
    messages = [ChatMessage.create_user_message("First message")]
    
    # First execution
    task_request1 = AgentTaskRequest.create_execute_task(
        agent_id="test-agent-456",
        messages=messages,
        session_id="reuse-session"
    )
    
    task_id1 = await tm.submit_task(task_request1)
    result1 = await tm.get_task_result(task_id1, timeout_seconds=10)
    
    # Check that instance was created
    instances_before = await tm.list_agent_instances()
    assert len(instances_before) == 1
    assert instances_before[0]['session_id'] == "reuse-session"
    
    # Second execution with same session
    messages2 = [ChatMessage.create_user_message("Second message")]
    task_request2 = AgentTaskRequest.create_execute_task(
        agent_id="test-agent-456",
        messages=messages2,
        session_id="reuse-session"
    )
    
    task_id2 = await tm.submit_task(task_request2)
    result2 = await tm.get_task_result(task_id2, timeout_seconds=10)
    
    # Check that same instance was reused (still only 1 instance)
    instances_after = await tm.list_agent_instances()
    assert len(instances_after) == 1
    assert instances_after[0]['message_count'] == 2  # Should have processed 2 messages


@pytest.mark.asyncio
async def test_streaming_execution(task_manager):
    """Test streaming task execution."""
    tm = await anext(task_manager)
    messages = [ChatMessage.create_user_message("Stream this response")]
    
    task_request = AgentTaskRequest.create_execute_task(
        agent_id="stream-agent",
        messages=messages,
        session_id="stream-session",
        stream=True
    )
    
    # Submit streaming task
    task_id = await tm.submit_task(task_request)
    
    # Collect stream chunks
    chunks = []
    async for chunk_data in tm.stream_task_results(task_id):
        chunks.append(chunk_data)
    
    # Verify streaming
    assert len(chunks) > 0
    
    # Check for content chunks
    content_chunks = [chunk for chunk in chunks if chunk.get('content')]
    assert len(content_chunks) > 0
    
    # Check for end marker
    end_chunks = [chunk for chunk in chunks if chunk.get('stream_end')]
    assert len(end_chunks) == 1


@pytest.mark.asyncio
async def test_instance_cleanup(task_manager):
    """Test automatic instance cleanup."""
    tm = await anext(task_manager)
    messages = [ChatMessage.create_user_message("Cleanup test")]
    
    task_request = AgentTaskRequest.create_execute_task(
        agent_id="cleanup-agent",
        messages=messages,
        session_id="cleanup-session"
    )
    
    # Execute task to create instance
    task_id = await tm.submit_task(task_request)
    result = await tm.get_task_result(task_id, timeout_seconds=10)
    
    # Verify instance exists
    instances = await tm.list_agent_instances()
    assert len(instances) == 1
    
    # Manual cleanup
    success = await tm.destroy_agent_instance("cleanup-agent", "cleanup-session")
    assert success
    
    # Verify instance removed
    instances_after = await tm.list_agent_instances()
    assert len(instances_after) == 0


@pytest.mark.asyncio
async def test_message_queue_integration(task_manager):
    """Test message queue integration."""
    tm = await anext(task_manager)
    # Check queue stats
    stats = await tm.message_queue.get_queue_stats(tm.TASK_QUEUE)
    assert stats.queue_name == tm.TASK_QUEUE
    
    # Submit multiple tasks
    tasks = []
    for i in range(3):
        messages = [ChatMessage.create_user_message(f"Message {i}")]
        task_request = AgentTaskRequest.create_execute_task(
            agent_id=f"queue-agent-{i}",
            messages=messages,
            session_id=f"queue-session-{i}",
            priority=MessagePriority.HIGH if i == 0 else MessagePriority.NORMAL
        )
        task_id = await tm.submit_task(task_request)
        tasks.append(task_id)
    
    # Wait for all results
    results = []
    for task_id in tasks:
        result = await tm.get_task_result(task_id, timeout_seconds=10)
        results.append(result)
    
    # Verify all tasks completed
    assert len(results) == 3
    for result in results:
        assert result is not None
        assert "Mock response" in result.message


@pytest.mark.asyncio  
async def test_concurrent_execution(task_manager):
    """Test concurrent task execution."""
    tm = await anext(task_manager)
    # Submit multiple tasks concurrently
    async def submit_task(i):
        messages = [ChatMessage.create_user_message(f"Concurrent message {i}")]
        task_request = AgentTaskRequest.create_execute_task(
            agent_id=f"concurrent-agent-{i}",
            messages=messages,
            session_id=f"concurrent-session-{i}"
        )
        task_id = await tm.submit_task(task_request)
        result = await tm.get_task_result(task_id, timeout_seconds=15)
        return result
    
    # Run 5 concurrent tasks
    results = await asyncio.gather(*[submit_task(i) for i in range(5)])
    
    # Verify all completed successfully
    assert len(results) == 5
    for i, result in enumerate(results):
        assert result is not None
        assert f"concurrent-agent-{i}" in result.agent_id
        assert "Mock response" in result.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
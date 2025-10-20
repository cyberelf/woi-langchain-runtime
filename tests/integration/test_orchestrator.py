"""Integration tests for Agent Orchestrator."""

import pytest
from unittest.mock import AsyncMock

import pytest_asyncio

from runtime.infrastructure.message_queues.in_memory import InMemoryMessageQueue
from runtime.core.agent_orchestrator import AgentOrchestrator, AgentMessageRequest, MessageType
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.domain.entities.agent import Agent
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.infrastructure.unit_of_work.in_memory_uow import TransactionalInMemoryUnitOfWork


@pytest_asyncio.fixture
async def orchestrator_setup():
    """Create orchestrator with real dependencies for integration testing."""
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    
    uow = TransactionalInMemoryUnitOfWork()
    
    # Create a test agent
    agent = Agent.create(
        name="Test Agent",
        template_id="test-template",
        template_version="1.0.0",
        configuration=AgentConfiguration(),
        metadata={"test": "metadata"}
    )
    
    # Store the agent
    async with uow:
        await uow.agents.save(agent)
        await uow.commit()
    
    # Mock framework executor to avoid LangGraph dependencies
    from runtime.core.executors import ExecutionResult, StreamingChunk
    
    framework_executor = AsyncMock()
    framework_executor.name = "mock_framework"
    framework_executor.version = "1.0.0"
    
    # Mock the agent_executor with proper execute method that returns ExecutionResult
    mock_agent_executor = AsyncMock()
    mock_agent_executor.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        message="Mock response",
        metadata={}
    ))
    
    # Mock stream_execute to return an async generator
    async def mock_stream_generator(*args, **kwargs):
        """Mock async generator for streaming."""
        yield StreamingChunk(content="Mock ", chunk_index=0)
        yield StreamingChunk(content="stream ", chunk_index=1)
        yield StreamingChunk(content="response", chunk_index=2, finish_reason="stop")
    
    mock_agent_executor.stream_execute = mock_stream_generator
    
    framework_executor.agent_executor = mock_agent_executor
    
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=framework_executor,
        max_workers=2,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )
    
    await orchestrator.initialize()
    
    yield orchestrator, agent
    
    # Cleanup
    await orchestrator.shutdown()
    await message_queue.shutdown()


@pytest.mark.asyncio
async def test_message_submission(orchestrator_setup):
    """Test basic message submission to orchestrator."""
    orchestrator, agent = orchestrator_setup
    
    # Create message request
    messages = [ChatMessage.create_user_message("Hello, test agent!")]
    message_request = AgentMessageRequest.create_execute_message(
        agent_id=agent.id.value,
        messages=messages,
        task_id="test-task-123",
        user_id="test-user"
    )
    
    # Submit message
    message_id = await orchestrator.submit_message(message_request)
    
    # Verify message was submitted
    assert message_id == message_request.message_id
    assert message_id is not None
    assert isinstance(message_id, str)


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator_setup):
    """Test that orchestrator initializes correctly."""
    orchestrator, agent = orchestrator_setup
    
    # Verify orchestrator state
    assert orchestrator._running is True
    assert len(orchestrator._message_workers) > 0
    
    # Verify message queue queues are created
    queues = await orchestrator.message_queue.list_queues()
    assert orchestrator.MESSAGE_QUEUE in queues


@pytest.mark.asyncio
async def test_agent_instance_management(orchestrator_setup):
    """Test agent instance creation and management."""
    orchestrator, agent = orchestrator_setup
    
    # Get or create agent instance
    instance = await orchestrator.get_or_create_agent_instance(
        agent_id=agent.id.value,
        task_id="test-task-instance"
    )
    
    # Verify instance was created
    assert instance is not None
    assert instance.agent_id == agent.id.value
    assert instance.task_id == "test-task-instance"
    
    # Verify instance is cached
    instance2 = await orchestrator.get_or_create_agent_instance(
        agent_id=agent.id.value,
        task_id="test-task-instance"
    )
    assert instance is instance2  # Should be the same instance


@pytest.mark.asyncio
async def test_multiple_message_types(orchestrator_setup):
    """Test submission of different message types."""
    orchestrator, agent = orchestrator_setup
    
    # Test execute message
    execute_request = AgentMessageRequest.create_execute_message(
        agent_id=agent.id.value,
        messages=[ChatMessage.create_user_message("Execute test")],
        task_id="test-execute",
        stream=False
    )
    
    execute_id = await orchestrator.submit_message(execute_request)
    assert execute_id == execute_request.message_id
    
    # Test streaming message (will be converted to execute in current implementation)
    stream_request = AgentMessageRequest.create_execute_message(
        agent_id=agent.id.value,
        messages=[ChatMessage.create_user_message("Stream test")],
        task_id="test-stream",
        stream=True
    )
    
    stream_id = await orchestrator.submit_message(stream_request)
    assert stream_id == stream_request.message_id


@pytest.mark.asyncio 
async def test_orchestrator_shutdown_cleanup(orchestrator_setup):
    """Test that orchestrator cleans up properly on shutdown."""
    orchestrator, agent = orchestrator_setup
    
    # Submit some messages first
    message_request = AgentMessageRequest.create_execute_message(
        agent_id=agent.id.value,
        messages=[ChatMessage.create_user_message("Cleanup test")],
        task_id="test-cleanup"
    )
    
    await orchestrator.submit_message(message_request)
    
    # Verify running state before shutdown
    assert orchestrator._running is True
    assert len(orchestrator._message_workers) > 0
    
    # Note: Actual shutdown is handled in the fixture cleanup
    # This test verifies the orchestrator is in a good state before shutdown
    stats = await orchestrator.message_queue.get_queue_stats(orchestrator.MESSAGE_QUEUE)
    assert stats is not None  # Should be able to get stats before shutdown

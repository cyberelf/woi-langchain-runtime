# test the execution of an agent

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from runtime.application.services.execute_agent_service import ExecuteAgentService
from runtime.application.commands.execute_agent_command import ExecuteAgentCommand
from runtime.domain.entities.agent import Agent
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.core.agent_orchestrator import AgentOrchestrator, AgentMessageRequest
from runtime.core.executors import StreamingChunk, ExecutionResult
from runtime.core.message_queue import MessagePriority
from runtime.infrastructure.message_queues.in_memory import InMemoryMessageQueue
from runtime.infrastructure.unit_of_work.in_memory_uow import TransactionalInMemoryUnitOfWork
from runtime.infrastructure.frameworks.langgraph.executor import LangGraphFrameworkExecutor
from runtime.service_config import ServicesConfig
from runtime.domain.value_objects.agent_configuration import AgentConfiguration

@pytest.mark.asyncio
async def test_execute_agent():
    """Test agent execution with proper orchestrator initialization."""
    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()
    
    # Create a test agent
    configuration = AgentConfiguration(
        llm_config_id="test",
    )
    
    agent = Agent.create(
        name="test-agent", 
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )
    
    # Store the agent in the unit of work
    async with uow:
        await uow.agents.save(agent)
        await uow.commit()
    
    # Setup LangGraph framework executor with test config
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(service_config=test_config.get_config_dict())
    
    # Create and initialize orchestrator
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=framework_executor,
        max_workers=2,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )
    
    # Initialize the orchestrator
    await orchestrator.initialize()
    
    try:
        # Create execute agent service
        service = ExecuteAgentService(orchestrator)
        
        # Create execution command
        command = ExecuteAgentCommand(
            agent_id=str(agent.id.value),
            messages=[
                ChatMessage(
                    role=MessageRole.USER,
                    content="Hello, test message"
                )
            ],
            task_id="test-task",
            user_id="test-user",
            stream=False,
            temperature=0.7,
            max_tokens=100
        )
        
        # Execute the agent
        result = await service.execute(command)
        
        # Verify result
        assert result is not None
        assert result.agent_id == str(agent.id.value)
        assert result.success is True
        print(f"Execution result: success={result.success}, message: {result.message}")
        
    finally:
        # Cleanup
        await orchestrator.shutdown()
        await message_queue.shutdown()


@pytest.mark.asyncio
async def test_streaming_execution_basic():
    """Test basic streaming execution functionality."""
    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()

    # Create a test agent
    configuration = AgentConfiguration(
        llm_config_id="test",
    )

    agent = Agent.create(
        name="test-streaming-agent",
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )

    # Store the agent in the unit of work
    async with uow:
        await uow.agents.save(agent)
        await uow.commit()

    # Setup LangGraph framework executor with test config
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(service_config=test_config.get_config_dict())

    # Create and initialize orchestrator
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=framework_executor,
        max_workers=2,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )

    await orchestrator.initialize()

    try:
        # Create execute agent service
        service = ExecuteAgentService(orchestrator)

        # Create streaming execution command
        command = ExecuteAgentCommand(
            agent_id=str(agent.id.value),
            messages=[
                ChatMessage(
                    role=MessageRole.USER,
                    content="Hello, please respond with a streaming response"
                )
            ],
            task_id="test-streaming-task",
            user_id="test-user",
            stream=True,
            temperature=0.7,
            max_tokens=100
        )

        # Execute streaming agent
        chunk_count = 0
        total_content = ""
        finish_reasons = []

        async for chunk in service.execute_streaming(command):
            chunk_count += 1
            print(f"Chunk {chunk_count}: content='{chunk.content}', finish_reason={chunk.finish_reason}")
            total_content += chunk.content

            # Verify chunk structure
            assert chunk.message_id is not None
            assert chunk.task_id is not None
            assert chunk.metadata.get('agent_id') == str(agent.id.value)

            if chunk.finish_reason:
                finish_reasons.append(chunk.finish_reason)

        # Verify streaming results
        assert chunk_count > 0, "Should receive at least one chunk"
        assert len(total_content) > 0, "Should have some content"
        assert len(finish_reasons) > 0, "Should have a finish reason"

        print(f"Streaming completed: {chunk_count} chunks, {len(total_content)} chars")

    finally:
        await orchestrator.shutdown()
        await message_queue.shutdown()


@pytest.mark.asyncio
async def test_streaming_execution_multiple_chunks():
    """Test streaming execution with multiple content chunks."""
    # Mock framework executor for controlled testing
    mock_framework_executor = MagicMock()
    mock_agent_executor = AsyncMock()

    # Simulate multiple streaming chunks
    async def mock_stream_execute(*args, **kwargs):
        chunks = [
            StreamingChunk(content="Hello ", chunk_index=0),
            StreamingChunk(content="there! ", chunk_index=1),
            StreamingChunk(content="This is a ", chunk_index=2),
            StreamingChunk(content="streaming response.", chunk_index=3, finish_reason="stop")
        ]
        for chunk in chunks:
            yield chunk

    mock_agent_executor.stream_execute = mock_stream_execute
    mock_framework_executor.agent_executor = mock_agent_executor
    mock_framework_executor.initialize = AsyncMock()
    mock_framework_executor.shutdown = AsyncMock()

    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()

    # Create test agent
    configuration = AgentConfiguration(llm_config_id="test")
    agent = Agent.create(
        name="test-multi-chunk",
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )

    async with uow:
        await uow.agents.save(agent)
        await uow.commit()

    # Create orchestrator with mock executor
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=mock_framework_executor,
        max_workers=1,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )

    await orchestrator.initialize()

    try:
        service = ExecuteAgentService(orchestrator)

        command = ExecuteAgentCommand(
            agent_id=str(agent.id.value),
            messages=[
                ChatMessage(role=MessageRole.USER, content="Test multiple chunks")
            ],
            task_id="multi-chunk-task",
            user_id="test-user",
            stream=True
        )

        # Collect all chunks
        chunks = []
        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)

        # Verify multiple chunks
        assert len(chunks) == 4, f"Expected 4 chunks, got {len(chunks)}"
        assert chunks[0].content == "Hello "
        assert chunks[1].content == "there! "
        assert chunks[2].content == "This is a "
        assert chunks[3].content == "streaming response."
        assert chunks[3].finish_reason == "stop"

        # Verify metadata consistency
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.metadata.get('agent_id') == str(agent.id.value)
            assert chunk.message_id is not None
            assert chunk.task_id == "multi-chunk-task"

        print(f"Multi-chunk test: {len(chunks)} chunks received")

    finally:
        await orchestrator.shutdown()
        await message_queue.shutdown()


@pytest.mark.asyncio
async def test_streaming_execution_error_handling():
    """Test streaming execution error handling."""
    # Mock framework executor that raises an exception
    mock_framework_executor = MagicMock()
    mock_agent_executor = AsyncMock()

    async def mock_stream_execute_with_error(*args, **kwargs):
        # Simulate an error during streaming
        yield StreamingChunk(content="Starting response", chunk_index=0)
        raise Exception("Simulated streaming error")

    mock_agent_executor.stream_execute = mock_stream_execute_with_error
    mock_framework_executor.agent_executor = mock_agent_executor
    mock_framework_executor.initialize = AsyncMock()
    mock_framework_executor.shutdown = AsyncMock()

    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()

    # Create test agent
    configuration = AgentConfiguration(llm_config_id="test")
    agent = Agent.create(
        name="test-error-streaming",
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )

    async with uow:
        await uow.agents.save(agent)
        await uow.commit()

    # Create orchestrator
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=mock_framework_executor,
        max_workers=1,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )

    await orchestrator.initialize()

    try:
        service = ExecuteAgentService(orchestrator)

        command = ExecuteAgentCommand(
            agent_id=str(agent.id.value),
            messages=[
                ChatMessage(role=MessageRole.USER, content="Test error handling")
            ],
            task_id="error-task",
            user_id="test-user",
            stream=True
        )

        # Should handle error gracefully
        chunks = []
        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)

        # Should receive at least one chunk before error
        assert len(chunks) > 0, "Should receive chunks before error"

        # Last chunk should have finish_reason="error"
        assert chunks[-1].finish_reason == "error"
        assert chunks[-1].content == ""
        assert "error" in chunks[-1].metadata

        print(f"Error handling test: {len(chunks)} chunks, last chunk finish_reason: {chunks[-1].finish_reason}")

    finally:
        await orchestrator.shutdown()
        await message_queue.shutdown()


@pytest.mark.asyncio
async def test_streaming_execution_with_timeout():
    """Test streaming execution with timeout scenarios."""
    # Mock framework executor that simulates timeout
    mock_framework_executor = MagicMock()
    mock_agent_executor = AsyncMock()

    async def mock_stream_execute_slow(*args, **kwargs):
        # Simulate very slow streaming
        yield StreamingChunk(content="First chunk", chunk_index=0)
        await asyncio.sleep(2)  # Simulate delay
        yield StreamingChunk(content="Second chunk", chunk_index=1, finish_reason="stop")

    mock_agent_executor.stream_execute = mock_stream_execute_slow
    mock_framework_executor.agent_executor = mock_agent_executor
    mock_framework_executor.initialize = AsyncMock()
    mock_framework_executor.shutdown = AsyncMock()

    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()

    # Create test agent
    configuration = AgentConfiguration(llm_config_id="test")
    agent = Agent.create(
        name="test-timeout-streaming",
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )

    async with uow:
        await uow.agents.save(agent)
        await uow.commit()

    # Create orchestrator with short timeout
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=mock_framework_executor,
        max_workers=1,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )

    await orchestrator.initialize()

    try:
        service = ExecuteAgentService(orchestrator)

        command = ExecuteAgentCommand(
            agent_id=str(agent.id.value),
            messages=[
                ChatMessage(role=MessageRole.USER, content="Test timeout")
            ],
            task_id="timeout-task",
            user_id="test-user",
            stream=True
        )

        # Execute with timeout - should handle gracefully
        chunks = []
        start_time = asyncio.get_event_loop().time()

        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)
            # Should timeout before second chunk
            if len(chunks) > 1:
                break

        elapsed = asyncio.get_event_loop().time() - start_time
        print(f"Timeout test: {len(chunks)} chunks in {elapsed:.2f}s")

        # Should receive at least the first chunk
        assert len(chunks) >= 1, "Should receive at least one chunk"

    finally:
        await orchestrator.shutdown()
        await message_queue.shutdown()


@pytest.mark.asyncio
async def test_streaming_execution_metadata():
    """Test streaming execution metadata preservation."""
    # Mock framework executor
    mock_framework_executor = MagicMock()
    mock_agent_executor = AsyncMock()

    async def mock_stream_execute_with_metadata(*args, **kwargs):
        # Extract metadata from kwargs
        metadata = kwargs.get('metadata', {})

        yield StreamingChunk(
            content="Response with metadata",
            chunk_index=0,
            finish_reason="stop",
            task_id=metadata.get('task_id'),
            context_id=metadata.get('context_id'),
            metadata={
                'test_metadata': 'test_value',
            }
        )

    mock_agent_executor.stream_execute = mock_stream_execute_with_metadata
    mock_framework_executor.agent_executor = mock_agent_executor
    mock_framework_executor.initialize = AsyncMock()
    mock_framework_executor.shutdown = AsyncMock()

    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()

    # Create test agent
    configuration = AgentConfiguration(llm_config_id="test")
    agent = Agent.create(
        name="test-metadata-streaming",
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )

    async with uow:
        await uow.agents.save(agent)
        await uow.commit()

    # Create orchestrator
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=mock_framework_executor,
        max_workers=1,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )

    await orchestrator.initialize()

    try:
        service = ExecuteAgentService(orchestrator)

        command = ExecuteAgentCommand(
            agent_id=str(agent.id.value),
            messages=[
                ChatMessage(role=MessageRole.USER, content="Test metadata")
            ],
            task_id="metadata-task",
            user_id="test-user",
            stream=True,
            metadata={
                'custom_field': 'custom_value',
                'context_id': 'test-context'
            }
        )

        # Collect chunks
        chunks = []
        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)

        assert len(chunks) == 1, "Should receive one chunk"
        chunk = chunks[0]

        # Verify metadata preservation
        assert chunk.metadata.get('agent_id') == str(agent.id.value)
        assert chunk.metadata.get('context_id') == 'test-context'
        assert chunk.metadata.get('chunk_number') == 1
        assert chunk.task_id == "metadata-task"
        assert chunk.message_id is not None

        print(f"Metadata test: chunk metadata keys: {list(chunk.metadata.keys())}")

    finally:
        await orchestrator.shutdown()
        await message_queue.shutdown()


@pytest.mark.asyncio
async def test_streaming_execution_concurrent_tasks():
    """Test streaming execution with concurrent tasks."""
    # Mock framework executor
    mock_framework_executor = MagicMock()
    mock_agent_executor = AsyncMock()

    async def mock_stream_execute_concurrent(*args, **kwargs):
        metadata = kwargs.get('metadata', {})
        task_id = metadata.get('task_id', 'unknown')

        yield StreamingChunk(
            content=f"Response for {task_id}",
            chunk_index=0,
            finish_reason="stop"
        )

    mock_agent_executor.stream_execute = mock_stream_execute_concurrent
    mock_framework_executor.agent_executor = mock_agent_executor
    mock_framework_executor.initialize = AsyncMock()
    mock_framework_executor.shutdown = AsyncMock()

    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()

    # Create test agent
    configuration = AgentConfiguration(llm_config_id="test")
    agent = Agent.create(
        name="test-concurrent-streaming",
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )

    async with uow:
        await uow.agents.save(agent)
        await uow.commit()

    # Create orchestrator
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=mock_framework_executor,
        max_workers=3,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )

    await orchestrator.initialize()

    try:
        service = ExecuteAgentService(orchestrator)

        # Create multiple concurrent streaming requests
        task_ids = ['task-1', 'task-2', 'task-3']
        tasks = []

        for task_id in task_ids:
            command = ExecuteAgentCommand(
                agent_id=str(agent.id.value),
                messages=[
                    ChatMessage(role=MessageRole.USER, content=f"Test {task_id}")
                ],
                task_id=task_id,
                user_id="test-user",
                stream=True
            )
            tasks.append(service.execute_streaming(command))

        # Execute all streams concurrently
        async def collect_chunks(stream):
            chunks = []
            async for chunk in stream:
                chunks.append(chunk)
            return chunks

        results = await asyncio.gather(*[collect_chunks(stream) for stream in tasks], return_exceptions=True)

        # Verify all tasks received responses
        assert len(results) == 3, "Should have results for all 3 tasks"

        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                print(f"Task {task_ids[i]} failed with error: {result}")
                assert False, f"Task {task_ids[i]} should not fail"
            else:
                assert len(result) == 1, f"Task {task_ids[i]} should receive one chunk"
                assert task_ids[i] in result[0].content, f"Content should reference task {task_ids[i]}"
                assert result[0].task_id == task_ids[i], f"Task ID should match task {task_ids[i]}"

        print(f"Concurrent test: {len(task_ids)} tasks completed successfully")

    finally:
        await orchestrator.shutdown()
        await message_queue.shutdown()


@pytest.mark.asyncio
async def test_streaming_execution_empty_response():
    """Test streaming execution with empty/short responses."""
    # Mock framework executor that returns empty response
    mock_framework_executor = MagicMock()
    mock_agent_executor = AsyncMock()

    async def mock_stream_execute_empty(*args, **kwargs):
        # Yield empty content chunk
        yield StreamingChunk(content="", chunk_index=0, finish_reason="stop")

    mock_agent_executor.stream_execute = mock_stream_execute_empty
    mock_framework_executor.agent_executor = mock_agent_executor
    mock_framework_executor.initialize = AsyncMock()
    mock_framework_executor.shutdown = AsyncMock()

    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    await message_queue.initialize()
    uow = TransactionalInMemoryUnitOfWork()

    # Create test agent
    configuration = AgentConfiguration(llm_config_id="test")
    agent = Agent.create(
        name="test-empty-streaming",
        template_id="simple-test",
        template_version="1.0.0",
        configuration=configuration,
        metadata={}
    )

    async with uow:
        await uow.agents.save(agent)
        await uow.commit()

    # Create orchestrator
    orchestrator = AgentOrchestrator(
        message_queue=message_queue,
        uow=uow,
        framework_executor=mock_framework_executor,
        max_workers=1,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )

    await orchestrator.initialize()

    try:
        service = ExecuteAgentService(orchestrator)

        command = ExecuteAgentCommand(
            agent_id=str(agent.id.value),
            messages=[
                ChatMessage(role=MessageRole.USER, content="Test empty response")
            ],
            task_id="empty-task",
            user_id="test-user",
            stream=True
        )

        # Collect chunks
        chunks = []
        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)

        # Verify empty response handling
        assert len(chunks) == 1, "Should receive one chunk even with empty content"
        assert chunks[0].content == "", "Content should be empty"
        assert chunks[0].finish_reason == "stop", "Should have finish reason"
        assert chunks[0].message_id is not None, "Should have message ID"
        assert chunks[0].task_id == "empty-task", "Should have task ID"

        print(f"Empty response test: handled empty content gracefully")

    finally:
        await orchestrator.shutdown()
        await message_queue.shutdown()

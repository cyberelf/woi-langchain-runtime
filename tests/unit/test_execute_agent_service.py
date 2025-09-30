"""Unit tests for ExecuteAgentService."""

from openai import Stream
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from runtime.application.services.execute_agent_service import ExecuteAgentService
from runtime.application.commands.execute_agent_command import ExecuteAgentCommand
from runtime.core.executors.interfaces import StreamingChunk
from runtime.domain.value_objects.chat_message import ChatMessage
from runtime.core.executors import ExecutionResult
from runtime.core.message_queue import MessagePriority


class TestExecuteAgentService:
    """Test the ExecuteAgentService application service."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock agent orchestrator."""
        orchestrator = AsyncMock()
        return orchestrator

    @pytest.fixture
    def service(self, mock_orchestrator):
        """Create service instance with mocked orchestrator."""
        return ExecuteAgentService(mock_orchestrator)

    @pytest.fixture
    def sample_messages(self):
        """Create sample chat messages."""
        return [
            ChatMessage.create_user_message("Hello, how are you?"),
            ChatMessage.create_assistant_message("I'm doing well, thank you!")
        ]

    @pytest.fixture
    def sample_command(self, sample_messages):
        """Create sample execute agent command."""
        return ExecuteAgentCommand(
            agent_id="test-agent-123",
            messages=sample_messages,
            temperature=0.7,
            max_tokens=1000,
            session_id="test-session",
            user_id="test-user",
            stream=False,
            metadata={"context": "test"}
        )

    @pytest.fixture
    def sample_execution_result(self):
        """Create sample execution result."""
        return ExecutionResult(
            success=True,
            agent_id="test-agent-123",
            task_id="test-session",
            message="Test response from agent",
            metadata={"tokens_used": 50}
        )

    @pytest.mark.asyncio
    async def test_execute_non_streaming(
        self, service, sample_command, mock_orchestrator, sample_execution_result
    ):
        """Test non-streaming agent execution."""
        # Setup mocks for the actual methods called
        mock_orchestrator.submit_message.return_value = "test-message-id-123"
        mock_orchestrator.get_message_result.return_value = sample_execution_result
        
        # Execute
        result = await service.execute(sample_command)
        
        # Verify result
        assert isinstance(result, ExecutionResult)
        assert result.agent_id == "test-agent-123"
        assert result.task_id == "test-session"
        assert result.message == "Test response from agent"
        assert result.success is True
        
        # Verify orchestrator was called correctly
        mock_orchestrator.submit_message.assert_called_once()
        mock_orchestrator.get_message_result.assert_called_once_with(
            "test-message-id-123", 300
        )
        
        # Check the AgentMessageRequest passed to submit_message
        call_args = mock_orchestrator.submit_message.call_args[0][0]
        assert call_args.agent_id == "test-agent-123"
        assert call_args.messages == sample_command.messages
        assert call_args.temperature == 0.7
        assert call_args.max_tokens == 1000
        assert call_args.task_id == "test-session"  # session_id maps to task_id
        assert call_args.user_id == "test-user"
        assert call_args.metadata == {"context": "test"}

    @pytest.mark.asyncio
    async def test_execute_with_generated_task_id(
        self, service, mock_orchestrator, sample_execution_result, sample_messages
    ):
        """Test execution with generated task_id when session_id is None."""
        command = ExecuteAgentCommand(
            agent_id="test-agent-456",
            messages=sample_messages,
            session_id=None  # No session_id provided
        )
        
        # Setup mocks
        mock_orchestrator.submit_message.return_value = "test-message-id-456"
        mock_orchestrator.get_message_result.return_value = sample_execution_result
        
        with patch('runtime.application.services.execute_agent_service.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "generated-uuid-123"
            
            await service.execute(command)
            
            # Verify UUID was generated for task_id
            mock_uuid.assert_called()
            
            # Verify the generated UUID was used as task_id
            call_args = mock_orchestrator.submit_message.call_args[0][0]
            assert call_args.task_id == "generated-uuid-123"

    @pytest.mark.asyncio
    async def test_execute_streaming(self, service, sample_messages, mock_orchestrator):
        """Test streaming agent execution."""
        command = ExecuteAgentCommand(
            agent_id="test-agent-streaming",
            messages=sample_messages,
            stream=True
        )
        
        # Setup mocks for streaming
        mock_orchestrator.submit_message.return_value = "test-streaming-message-id"

        def create_streaming_chunk(content, finish_reason=None):
            return StreamingChunk(
                content=content,
                finish_reason=finish_reason,
                chunk_index=0,
                metadata={}
            )
        
        # Create mock streaming chunk data (as dict, as returned by orchestrator)
        async def mock_stream_results(message_id: str):
            yield create_streaming_chunk("Hello")
            yield create_streaming_chunk(" world")
            yield create_streaming_chunk("!", finish_reason="stop")
        
        mock_orchestrator.stream_message_results = mock_stream_results
        
        # Execute streaming
        chunks = []
        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)
        
        # Verify chunks (service converts dict to StreamingChunk)
        assert len(chunks) == 3
        assert chunks[0].content == "Hello"
        assert chunks[0].finish_reason is None
        assert chunks[1].content == " world" 
        assert chunks[1].finish_reason is None
        assert chunks[2].content == "!"
        assert chunks[2].finish_reason == "stop"
        
        # Verify orchestrator methods were called correctly
        mock_orchestrator.submit_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_execution_error(self, service, sample_command, mock_orchestrator):
        """Test execution when orchestrator raises an error."""
        # Setup mock to raise an exception from submit_message
        mock_orchestrator.submit_message.side_effect = Exception("Orchestrator error")
        
        # Execute and verify exception propagates
        with pytest.raises(Exception, match="Orchestrator error"):
            await service.execute(sample_command)

    @pytest.mark.asyncio
    async def test_stream_with_execution_error(self, service, sample_messages, mock_orchestrator):
        """Test streaming when orchestrator raises an error."""
        command = ExecuteAgentCommand(
            agent_id="test-agent",
            messages=sample_messages,
            stream=True
        )
        
        # Setup mocks - submit_message succeeds but stream_message_results fails
        mock_orchestrator.submit_message.return_value = "error-message-id"
        
        # Replace the mock method with one that raises an exception
        async def stream_message_results_error_mock(message_id: str):
            raise Exception("Streaming error")
            yield  # This won't be reached but makes it an async generator
        
        mock_orchestrator.stream_message_results = stream_message_results_error_mock
        
        # Execute streaming and verify exception handling
        chunks = []
        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)
        
        # Service should yield error chunk instead of propagating exception
        assert len(chunks) == 1
        assert chunks[0].finish_reason == "error"
        assert "Streaming error" in chunks[0].metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_logging_execution_start(
        self, service, sample_command, mock_orchestrator, sample_execution_result
    ):
        """Test that execution start is logged."""
        # Setup mocks
        mock_orchestrator.submit_message.return_value = "log-test-message-id"
        mock_orchestrator.get_message_result.return_value = sample_execution_result
        
        with patch('runtime.application.services.execute_agent_service.logger') as mock_logger:
            await service.execute(sample_command)
            
            # Verify logging
            mock_logger.info.assert_any_call("🚀 Executing agent: test-agent-123")
            mock_logger.debug.assert_called()  # Task ID logging

    @pytest.mark.asyncio
    async def test_logging_streaming_start(self, service, sample_messages, mock_orchestrator):
        """Test that streaming start is logged."""
        command = ExecuteAgentCommand(
            agent_id="test-agent-stream",
            messages=sample_messages,
            stream=True
        )
        
        # Setup mocks for streaming
        mock_orchestrator.submit_message.return_value = "log-stream-message-id"
        
        async def mock_stream_results():
            yield {"content": "test", "finish_reason": "stop"}
        
        mock_orchestrator.stream_message_results.return_value = mock_stream_results()
        
        with patch('runtime.application.services.execute_agent_service.logger') as mock_logger:
            async for _ in service.execute_streaming(command):
                pass
            
            # Verify logging
            mock_logger.info.assert_any_call("Streaming execution for agent: test-agent-stream")

    @pytest.mark.asyncio
    async def test_priority_mapping(
        self, service, sample_messages, mock_orchestrator, sample_execution_result
    ):
        """Test that message priority is correctly mapped."""
        command = ExecuteAgentCommand(
            agent_id="test-agent",
            messages=sample_messages,
            metadata={"priority": "high"}
        )
        
        # Setup mocks
        mock_orchestrator.submit_message.return_value = "priority-test-message-id"
        mock_orchestrator.get_message_result.return_value = sample_execution_result
        
        await service.execute(command)
        
        # Verify the message request was created with correct priority
        call_args = mock_orchestrator.submit_message.call_args[0][0]
        # The priority should be set to default (NORMAL)
        assert hasattr(call_args, 'priority')
        assert call_args.priority == MessagePriority.NORMAL

    @pytest.mark.asyncio
    async def test_correlation_id_generation(
        self, service, sample_command, mock_orchestrator, sample_execution_result
    ):
        """Test that correlation ID is generated for each request."""
        # Setup mocks
        mock_orchestrator.submit_message.return_value = "correlation-test-message-id"
        mock_orchestrator.get_message_result.return_value = sample_execution_result
        
        with patch('runtime.application.services.execute_agent_service.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.__str__ = MagicMock(return_value="correlation-123")
            
            await service.execute(sample_command)
            
            # Verify UUID was called for both task_id (if needed) and correlation_id
            assert mock_uuid.call_count >= 1
            
            # Verify correlation_id was set
            call_args = mock_orchestrator.submit_message.call_args[0][0]
            assert hasattr(call_args, 'correlation_id')
            assert call_args.correlation_id is not None

    def test_service_initialization(self, mock_orchestrator):
        """Test service initialization."""
        service = ExecuteAgentService(mock_orchestrator)
        
        assert service.orchestrator is mock_orchestrator

    @pytest.mark.asyncio
    async def test_execute_with_minimal_command(self, service, mock_orchestrator, sample_execution_result):
        """Test execution with minimal command parameters."""
        messages = [ChatMessage.create_user_message("Simple question")]
        command = ExecuteAgentCommand(
            agent_id="simple-agent",
            messages=messages
            # No optional parameters
        )
        
        # Setup mocks
        mock_orchestrator.submit_message.return_value = "minimal-command-message-id"
        mock_orchestrator.get_message_result.return_value = sample_execution_result
        
        result = await service.execute(command)
        
        # Should execute successfully with defaults
        assert result is sample_execution_result
        
        # Verify orchestrator was called
        mock_orchestrator.submit_message.assert_called_once()
        mock_orchestrator.get_message_result.assert_called_once()
        
        call_args = mock_orchestrator.submit_message.call_args[0][0]
        assert call_args.agent_id == "simple-agent"
        assert call_args.messages == messages

    @pytest.mark.asyncio
    async def test_stream_empty_generator(self, service, sample_messages, mock_orchestrator):
        """Test streaming with empty response."""
        command = ExecuteAgentCommand(
            agent_id="empty-agent",
            messages=sample_messages,
            stream=True
        )
        
        # Setup mocks for streaming
        mock_orchestrator.submit_message.return_value = "empty-stream-message-id"
        
        # Empty async generator
        async def empty_stream_results(message_id: str):
            return
            yield  # Unreachable but makes it a generator
        
        mock_orchestrator.stream_message_results = empty_stream_results
        
        chunks = []
        async for chunk in service.execute_streaming(command):
            chunks.append(chunk)
        
        # Should handle empty stream gracefully
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_message_request_creation(
        self, service, sample_command, mock_orchestrator, sample_execution_result
    ):
        """Test that AgentMessageRequest is created correctly."""
        # Setup mocks
        mock_orchestrator.submit_message.return_value = "message-request-test-id"
        mock_orchestrator.get_message_result.return_value = sample_execution_result
        
        await service.execute(sample_command)
        
        # Get the AgentMessageRequest that was passed
        call_args = mock_orchestrator.submit_message.call_args[0][0]
        
        # Verify all command fields are correctly mapped
        assert call_args.agent_id == sample_command.agent_id
        assert call_args.messages == sample_command.messages
        assert call_args.temperature == sample_command.temperature
        assert call_args.max_tokens == sample_command.max_tokens
        assert call_args.task_id == sample_command.session_id  # session_id maps to task_id
        assert call_args.user_id == sample_command.user_id
        assert call_args.metadata == sample_command.metadata
        
        # Should have generated correlation_id
        assert hasattr(call_args, 'correlation_id')
        assert call_args.correlation_id is not None

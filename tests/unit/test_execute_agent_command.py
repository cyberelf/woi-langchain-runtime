"""Unit tests for ExecuteAgentCommand."""

import pytest

from runtime.application.commands.execute_agent_command import ExecuteAgentCommand
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole


class TestExecuteAgentCommand:
    """Test the ExecuteAgentCommand."""

    @pytest.fixture
    def sample_messages(self):
        """Create sample chat messages."""
        return [
            ChatMessage.create_user_message("Hello, how are you?"),
            ChatMessage.create_assistant_message("I'm doing well, thank you!"),
            ChatMessage.create_user_message("Can you help me with a task?")
        ]

    def test_create_command_with_all_fields(self, sample_messages):
        """Test creating command with all fields."""
        command = ExecuteAgentCommand(
            agent_id="test-agent-123",
            messages=sample_messages,
            temperature=0.8,
            max_tokens=1500,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stream=True,
            stop=["<END>", "\n\n"],
            session_id="session-456",
            user_id="user-789",
            metadata={"context": "test", "priority": "high"}
        )

        assert command.agent_id == "test-agent-123"
        assert command.messages == sample_messages
        assert command.temperature == 0.8
        assert command.max_tokens == 1500
        assert command.top_p == 0.9
        assert command.frequency_penalty == 0.5
        assert command.presence_penalty == 0.3
        assert command.stream is True
        assert command.stop == ["<END>", "\n\n"]
        assert command.session_id == "session-456"
        assert command.user_id == "user-789"
        assert command.metadata == {"context": "test", "priority": "high"}

    def test_create_command_with_minimal_fields(self, sample_messages):
        """Test creating command with minimal required fields."""
        command = ExecuteAgentCommand(
            agent_id="minimal-agent",
            messages=sample_messages
        )

        assert command.agent_id == "minimal-agent"
        assert command.messages == sample_messages
        assert command.temperature is None
        assert command.max_tokens is None
        assert command.top_p is None
        assert command.frequency_penalty is None
        assert command.presence_penalty is None
        assert command.stream is False  # Default value
        assert command.stop is None
        assert command.session_id is None
        assert command.user_id is None
        assert command.metadata is None

    def test_validation_empty_agent_id(self, sample_messages):
        """Test that empty agent_id raises ValueError."""
        with pytest.raises(ValueError, match="Agent ID is required"):
            ExecuteAgentCommand(
                agent_id="",
                messages=sample_messages
            )

    def test_validation_none_agent_id(self, sample_messages):
        """Test that None agent_id raises ValueError."""
        with pytest.raises(ValueError, match="Agent ID is required"):
            ExecuteAgentCommand(
                agent_id=None,  # type: ignore
                messages=sample_messages
            )

    def test_validation_empty_messages_list(self):
        """Test that empty messages list raises ValueError."""
        with pytest.raises(ValueError, match="Messages list cannot be empty"):
            ExecuteAgentCommand(
                agent_id="test-agent",
                messages=[]
            )

    def test_validation_none_messages(self):
        """Test that None messages raises ValueError."""
        with pytest.raises(ValueError, match="Messages list cannot be empty"):
            ExecuteAgentCommand(
                agent_id="test-agent",
                messages=None  # pyright: ignore
            )

    def test_validation_temperature_too_low(self, sample_messages):
        """Test that temperature < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
            ExecuteAgentCommand(
                agent_id="test-agent",
                messages=sample_messages,
                temperature=-0.1
            )

    def test_validation_temperature_too_high(self, sample_messages):
        """Test that temperature > 2.0 raises ValueError."""
        with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
            ExecuteAgentCommand(
                agent_id="test-agent",
                messages=sample_messages,
                temperature=2.1
            )

    def test_validation_temperature_boundary_values(self, sample_messages):
        """Test that temperature boundary values (0.0, 2.0) are valid."""
        # Should not raise exception
        command1 = ExecuteAgentCommand(
            agent_id="test-agent",
            messages=sample_messages,
            temperature=0.0
        )
        assert command1.temperature == 0.0

        command2 = ExecuteAgentCommand(
            agent_id="test-agent",
            messages=sample_messages,
            temperature=2.0
        )
        assert command2.temperature == 2.0

    def test_validation_max_tokens_zero(self, sample_messages):
        """Test that max_tokens = 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ExecuteAgentCommand(
                agent_id="test-agent",
                messages=sample_messages,
                max_tokens=0
            )

    def test_validation_max_tokens_negative(self, sample_messages):
        """Test that negative max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ExecuteAgentCommand(
                agent_id="test-agent",
                messages=sample_messages,
                max_tokens=-100
            )

    def test_validation_max_tokens_positive(self, sample_messages):
        """Test that positive max_tokens is valid."""
        command = ExecuteAgentCommand(
            agent_id="test-agent",
            messages=sample_messages,
            max_tokens=1000
        )
        assert command.max_tokens == 1000

    def test_with_single_message(self):
        """Test command with single message."""
        message = ChatMessage.create_user_message("Single message test")
        command = ExecuteAgentCommand(
            agent_id="single-message-agent",
            messages=[message]
        )

        assert len(command.messages) == 1
        assert command.messages[0] == message

    def test_with_mixed_message_roles(self):
        """Test command with mixed message roles."""
        messages = [
            ChatMessage.create_system_message("You are a helpful assistant"),
            ChatMessage.create_user_message("Hello"),
            ChatMessage.create_assistant_message("Hi there!"),
            ChatMessage(role=MessageRole.TOOL, content="Tool result: Success")
        ]

        command = ExecuteAgentCommand(
            agent_id="mixed-roles-agent",
            messages=messages
        )

        assert len(command.messages) == 4
        assert command.messages[0].role == MessageRole.SYSTEM
        assert command.messages[1].role == MessageRole.USER
        assert command.messages[2].role == MessageRole.ASSISTANT
        assert command.messages[3].role == MessageRole.TOOL

    def test_with_streaming_enabled(self, sample_messages):
        """Test command with streaming enabled."""
        command = ExecuteAgentCommand(
            agent_id="streaming-agent",
            messages=sample_messages,
            stream=True
        )

        assert command.stream is True

    def test_with_stop_sequences(self, sample_messages):
        """Test command with stop sequences."""
        stop_sequences = ["<|endoftext|>", "\n\nHuman:", "STOP"]
        command = ExecuteAgentCommand(
            agent_id="stop-agent",
            messages=sample_messages,
            stop=stop_sequences
        )

        assert command.stop == stop_sequences

    def test_with_all_penalties(self, sample_messages):
        """Test command with all penalty parameters."""
        command = ExecuteAgentCommand(
            agent_id="penalty-agent",
            messages=sample_messages,
            frequency_penalty=0.7,
            presence_penalty=0.3
        )

        assert command.frequency_penalty == 0.7
        assert command.presence_penalty == 0.3

    def test_with_top_p_sampling(self, sample_messages):
        """Test command with top_p parameter."""
        command = ExecuteAgentCommand(
            agent_id="top-p-agent",
            messages=sample_messages,
            top_p=0.95
        )

        assert command.top_p == 0.95

    def test_with_session_and_user_context(self, sample_messages):
        """Test command with session and user context."""
        command = ExecuteAgentCommand(
            agent_id="context-agent",
            messages=sample_messages,
            session_id="conversation-session-123",
            user_id="user-profile-456"
        )

        assert command.session_id == "conversation-session-123"
        assert command.user_id == "user-profile-456"

    def test_with_complex_metadata(self, sample_messages):
        """Test command with complex metadata."""
        metadata = {
            "conversation_context": {
                "topic": "technical_support",
                "urgency": "high",
                "previous_issues": ["login", "password_reset"]
            },
            "user_preferences": {
                "language": "en-US",
                "format": "detailed"
            },
            "tracking": {
                "source": "web_chat",
                "campaign_id": "support-2024-q1"
            }
        }

        command = ExecuteAgentCommand(
            agent_id="metadata-agent",
            messages=sample_messages,
            metadata=metadata
        )

        assert command.metadata == metadata


    def test_with_float_temperature(self, sample_messages):
        """Test command with float temperature values."""
        command = ExecuteAgentCommand(
            agent_id="float-temp-agent",
            messages=sample_messages,
            temperature=0.73
        )

        assert command.temperature == 0.73

    def test_with_integer_temperature(self, sample_messages):
        """Test command with integer temperature values."""
        command = ExecuteAgentCommand(
            agent_id="int-temp-agent",
            messages=sample_messages,
            temperature=1  # Integer that should be valid
        )

        assert command.temperature == 1

    def test_messages_list_preserves_order(self):
        """Test that messages list preserves order."""
        messages = [
            ChatMessage.create_user_message("First"),
            ChatMessage.create_assistant_message("Second"),
            ChatMessage.create_user_message("Third"),
            ChatMessage.create_assistant_message("Fourth")
        ]

        command = ExecuteAgentCommand(
            agent_id="order-agent",
            messages=messages
        )

        # Order should be preserved
        assert command.messages[0].content == "First"
        assert command.messages[1].content == "Second"
        assert command.messages[2].content == "Third"
        assert command.messages[3].content == "Fourth"


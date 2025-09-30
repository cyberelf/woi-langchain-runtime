"""Unit tests for ChatMessage value object."""

import pytest
from datetime import datetime, UTC

from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole


class TestChatMessage:
    """Test the ChatMessage value object."""

    def test_create_user_message(self):
        """Test creating user message."""
        message = ChatMessage.create_user_message("Hello, world!")
        
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert isinstance(message.timestamp, datetime)
        assert message.metadata == {}
        assert message.is_user_message()
        assert not message.is_assistant_message()
        assert not message.is_system_message()

    def test_create_user_message_with_metadata(self):
        """Test creating user message with metadata."""
        metadata = {"session_id": "test-session", "user_id": "user-123"}
        message = ChatMessage.create_user_message("Hello!", metadata=metadata)
        
        assert message.role == MessageRole.USER
        assert message.content == "Hello!"
        assert message.metadata == metadata

    def test_create_assistant_message(self):
        """Test creating assistant message."""
        message = ChatMessage.create_assistant_message("Hi there!")
        
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Hi there!"
        assert isinstance(message.timestamp, datetime)
        assert message.metadata == {}
        assert message.is_assistant_message()
        assert not message.is_user_message()
        assert not message.is_system_message()

    def test_create_assistant_message_with_metadata(self):
        """Test creating assistant message with metadata."""
        metadata = {"confidence": 0.95, "model": "gpt-4"}
        message = ChatMessage.create_assistant_message("Response", metadata=metadata)
        
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Response"
        assert message.metadata == metadata

    def test_create_system_message(self):
        """Test creating system message."""
        message = ChatMessage.create_system_message("You are a helpful assistant")
        
        assert message.role == MessageRole.SYSTEM
        assert message.content == "You are a helpful assistant"
        assert isinstance(message.timestamp, datetime)
        assert message.metadata == {}
        assert message.is_system_message()
        assert not message.is_user_message()
        assert not message.is_assistant_message()

    def test_create_system_message_with_metadata(self):
        """Test creating system message with metadata."""
        metadata = {"context": "initial_setup"}
        message = ChatMessage.create_system_message("System prompt", metadata=metadata)
        
        assert message.role == MessageRole.SYSTEM
        assert message.content == "System prompt"
        assert message.metadata == metadata

    def test_direct_creation(self):
        """Test direct ChatMessage creation."""
        timestamp = datetime.now(UTC)
        metadata = {"test": "data"}
        
        message = ChatMessage(
            role=MessageRole.USER,
            content="Direct message",
            timestamp=timestamp,
            metadata=metadata
        )
        
        assert message.role == MessageRole.USER
        assert message.content == "Direct message"
        assert message.timestamp == timestamp
        assert message.metadata == metadata

    def test_validation_invalid_role(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Role must be a MessageRole enum"):
            ChatMessage(
                role="invalid_role",  # type: ignore
                content="Test message"
            )

    def test_validation_empty_content(self):
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            ChatMessage(
                role=MessageRole.USER,
                content=""
            )

    def test_validation_none_content(self):
        """Test that None content raises ValueError."""
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            ChatMessage(
                role=MessageRole.USER,
                content=None  # type: ignore
            )

    def test_validation_invalid_timestamp(self):
        """Test that invalid timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Timestamp must be a datetime"):
            ChatMessage(
                role=MessageRole.USER,
                content="Test message",
                timestamp="invalid_timestamp"  # type: ignore
            )

    def test_validation_invalid_metadata(self):
        """Test that invalid metadata raises ValueError."""
        with pytest.raises(ValueError, match="Metadata must be a dictionary"):
            ChatMessage(
                role=MessageRole.USER,
                content="Test message",
                metadata="invalid_metadata"  # pyright: ignore
            )


    def test_to_dict(self):
        """Test converting message to dictionary."""
        timestamp = datetime.now(UTC)
        metadata = {"session_id": "test-123"}
        
        message = ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Test response",
            timestamp=timestamp,
            metadata=metadata
        )
        
        message_dict = message.to_dict()
        
        assert message_dict["role"] == "assistant"
        assert message_dict["content"] == "Test response"
        assert message_dict["timestamp"] == timestamp.isoformat()
        assert message_dict["metadata"] == metadata

    def test_from_dict(self):
        """Test creating message from dictionary."""
        timestamp = datetime.now(UTC)
        message_dict = {
            "role": "user",
            "content": "Hello from dict",
            "timestamp": timestamp.isoformat(),
            "metadata": {"test": "data"}
        }
        
        message = ChatMessage.from_dict(message_dict)
        
        assert message.role == MessageRole.USER
        assert message.content == "Hello from dict"
        assert message.timestamp == timestamp
        assert message.metadata == {"test": "data"}

    def test_from_dict_minimal(self):
        """Test creating message from minimal dictionary."""
        message_dict = {
            "role": "assistant",
            "content": "Minimal response",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        message = ChatMessage.from_dict(message_dict)
        
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Minimal response"
        assert message.metadata == {}  # Default empty dict

    def test_from_dict_invalid_role(self):
        """Test creating message from dict with invalid role."""
        message_dict = {
            "role": "invalid_role",
            "content": "Test message",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        with pytest.raises(ValueError):
            ChatMessage.from_dict(message_dict)

    def test_role_checking_methods(self):
        """Test role checking methods for business logic."""
        user_msg = ChatMessage.create_user_message("User message")
        assistant_msg = ChatMessage.create_assistant_message("Assistant message") 
        system_msg = ChatMessage.create_system_message("System message")
        tool_msg = ChatMessage(role=MessageRole.TOOL, content="Tool result")
        
        # Test role checking business logic
        assert user_msg.is_user_message()
        assert not user_msg.is_assistant_message()
        assert not user_msg.is_system_message()
        
        assert assistant_msg.is_assistant_message()
        assert not assistant_msg.is_user_message()
        
        assert system_msg.is_system_message()
        assert not system_msg.is_user_message()
        
        # Tool messages don't have is_tool_message method, so test basic functionality
        assert tool_msg.role == MessageRole.TOOL

    def test_roundtrip_serialization(self):
        """Test that message can be serialized and deserialized."""
        original = ChatMessage.create_user_message(
            "Test message",
            metadata={"session_id": "test-123", "priority": "high"}
        )
        
        # Serialize to dict
        message_dict = original.to_dict()
        
        # Deserialize from dict
        restored = ChatMessage.from_dict(message_dict)
        
        # Should be equivalent
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.timestamp == original.timestamp
        assert restored.metadata == original.metadata

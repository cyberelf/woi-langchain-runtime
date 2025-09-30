"""Unit tests for AgentId value object."""

import pytest
import uuid

from runtime.domain.value_objects.agent_id import AgentId


class TestAgentId:
    """Test the AgentId value object."""

    def test_create_from_string(self):
        """Test creating AgentId from string."""
        agent_id = AgentId.from_string("test-agent-123")
        
        assert agent_id.value == "test-agent-123"
        assert str(agent_id) == "test-agent-123"

    def test_generate_unique_id(self):
        """Test generating unique agent IDs."""
        id1 = AgentId.generate()
        id2 = AgentId.generate()
        
        assert id1 != id2
        assert isinstance(uuid.UUID(id1.value), uuid.UUID)  # Valid UUID format
        assert isinstance(uuid.UUID(id2.value), uuid.UUID)  # Valid UUID format

    def test_validation_empty_value(self):
        """Test that empty value raises ValueError."""
        with pytest.raises(ValueError, match="Agent ID cannot be empty"):
            AgentId("")

    def test_validation_none_value(self):
        """Test that None value raises ValueError."""
        with pytest.raises(ValueError, match="Agent ID cannot be empty"):
            AgentId(None)  # type: ignore

    def test_validation_non_string_value(self):
        """Test that non-string value raises ValueError."""
        with pytest.raises(ValueError, match="Agent ID must be a string"):
            AgentId(123)  # pyright: ignore

    def test_equality_basic(self):
        """Test basic equality functionality for business logic."""
        id1 = AgentId.from_string("same-id")
        id2 = AgentId.from_string("same-id")
        id3 = AgentId.from_string("different-id")
        
        assert id1 == id2
        assert id1 != id3


"""Unit tests for Agent entity."""

import pytest
from datetime import datetime

from runtime.domain.entities.agent import Agent, AgentStatus
from runtime.domain.value_objects.agent_id import AgentId
from runtime.domain.value_objects.agent_configuration import AgentConfiguration


class TestAgent:
    """Test the Agent entity."""

    @pytest.fixture
    def sample_configuration(self):
        """Create sample configuration for testing."""
        return AgentConfiguration(
            system_prompt="You are a helpful assistant",
            llm_config_id="test-llm",
            conversation_config={"temperature": 0.7, "max_tokens": 1000},
            toolsets=["web_search"],
            template_config={"setting": "value"}
        )

    @pytest.fixture
    def sample_agent(self, sample_configuration):
        """Create sample agent for testing."""
        return Agent.create(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration,
            template_version="1.0.0",
            metadata={"test": "data"}
        )

    def test_agent_creation_with_all_fields(self, sample_configuration):
        """Test creating agent with all fields."""
        agent = Agent.create(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration,
            template_version="1.0.0",
            metadata={"test": "data"},
            agent_id="custom-id"
        )

        assert agent.name == "Test Agent"
        assert agent.template_id == "test-template"
        assert agent.template_version == "1.0.0"
        assert agent.configuration == sample_configuration
        assert agent.status == AgentStatus.CREATED
        assert agent.metadata == {"test": "data"}
        assert str(agent.id) == "custom-id"
        assert isinstance(agent.created_at, datetime)
        assert isinstance(agent.updated_at, datetime)

    def test_agent_creation_with_minimal_fields(self, sample_configuration):
        """Test creating agent with minimal required fields."""
        agent = Agent.create(
            name="Minimal Agent",
            template_id="minimal-template",
            configuration=sample_configuration
        )

        assert agent.name == "Minimal Agent"
        assert agent.template_id == "minimal-template"
        assert agent.template_version is None
        assert agent.configuration == sample_configuration
        assert agent.status == AgentStatus.CREATED
        assert agent.metadata == {}
        assert isinstance(agent.id, AgentId)

    def test_agent_validation_empty_name(self, sample_configuration):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            Agent.create(
                name="",
                template_id="test-template",
                configuration=sample_configuration
            )

    def test_agent_validation_empty_template_id(self, sample_configuration):
        """Test that empty template_id raises ValueError."""
        with pytest.raises(ValueError, match="Template ID cannot be empty"):
            Agent.create(
                name="Test Agent",
                template_id="",
                configuration=sample_configuration
            )

    def test_agent_validation_invalid_configuration(self):
        """Test that invalid configuration raises ValueError."""
        with pytest.raises(ValueError, match="Configuration must be an AgentConfiguration instance"):
            Agent.create(
                name="Test Agent",
                template_id="test-template",
                configuration={"invalid": "config"}  # type: ignore
            )

    def test_update_configuration(self, sample_agent):
        """Test updating agent configuration."""
        new_config = AgentConfiguration(
            system_prompt="New prompt",
            llm_config_id="new-llm"
        )
        
        original_updated_at = sample_agent.updated_at
        
        sample_agent.update_configuration(new_config)
        
        assert sample_agent.configuration == new_config
        assert sample_agent.updated_at > original_updated_at

    def test_update_configuration_invalid_type(self, sample_agent):
        """Test updating configuration with invalid type."""
        with pytest.raises(ValueError, match="Configuration must be an AgentConfiguration instance"):
            sample_agent.update_configuration({"invalid": "config"})

    def test_update_status(self, sample_agent):
        """Test updating agent status."""
        original_updated_at = sample_agent.updated_at
        
        sample_agent.update_status(AgentStatus.ACTIVE)
        
        assert sample_agent.status == AgentStatus.ACTIVE
        assert sample_agent.updated_at > original_updated_at

    def test_update_status_invalid_type(self, sample_agent):
        """Test updating status with invalid type."""
        with pytest.raises(ValueError, match="Status must be an AgentStatus enum"):
            sample_agent.update_status("invalid_status")

    def test_activate(self, sample_agent):
        """Test activating agent."""
        sample_agent.activate()
        assert sample_agent.status == AgentStatus.ACTIVE

    def test_deactivate(self, sample_agent):
        """Test deactivating agent."""
        sample_agent.deactivate()
        assert sample_agent.status == AgentStatus.INACTIVE

    def test_mark_error(self, sample_agent):
        """Test marking agent as error."""
        sample_agent.mark_error()
        assert sample_agent.status == AgentStatus.ERROR

    def test_is_active(self, sample_agent):
        """Test is_active method."""
        assert not sample_agent.is_active()  # Created status
        
        sample_agent.activate()
        assert sample_agent.is_active()
        
        sample_agent.deactivate()
        assert not sample_agent.is_active()

    def test_is_configured_properly(self, sample_agent):
        """Test is_configured_properly method."""
        assert sample_agent.is_configured_properly()
        
        # Test with empty template_id
        sample_agent.template_id = ""
        assert not sample_agent.is_configured_properly()

    def test_get_template_configuration(self, sample_agent):
        """Test getting template configuration."""
        template_config = sample_agent.get_template_configuration()
        
        assert "system_prompt" in template_config
        assert "llm_config_id" in template_config
        assert "toolset_configs" in template_config
        assert "temperature" in template_config
        assert "max_tokens" in template_config
        assert "setting" in template_config

    def test_get_execution_params(self, sample_agent):
        """Test getting execution parameters."""
        params = sample_agent.get_execution_params()
        
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 1000

    def test_get_toolset_names(self, sample_agent):
        """Test getting toolset names."""
        toolsets = sample_agent.get_toolset_names()
        assert toolsets == ["web_search"]

    def test_get_temperature(self, sample_agent):
        """Test getting temperature."""
        assert sample_agent.get_temperature() == 0.7

    def test_get_max_tokens(self, sample_agent):
        """Test getting max_tokens."""
        assert sample_agent.get_max_tokens() == 1000

    def test_get_system_prompt(self, sample_agent):
        """Test getting system prompt."""
        assert sample_agent.get_system_prompt() == "You are a helpful assistant"

    def test_get_llm_config_id(self, sample_agent):
        """Test getting LLM config ID."""
        assert sample_agent.get_llm_config_id() == "test-llm"

    def test_with_conversation_config(self, sample_agent):
        """Test creating agent with updated conversation config."""
        new_agent = sample_agent.with_conversation_config(
            temperature=0.9,
            max_tokens=2000
        )
        
        # Original agent unchanged
        assert sample_agent.get_temperature() == 0.7
        assert sample_agent.get_max_tokens() == 1000
        
        # New agent has updated config
        assert new_agent.get_temperature() == 0.9
        assert new_agent.get_max_tokens() == 2000
        assert new_agent.id == sample_agent.id  # Same ID
        assert new_agent.name == sample_agent.name  # Same name

    def test_add_metadata(self, sample_agent):
        """Test adding metadata."""
        original_updated_at = sample_agent.updated_at
        
        sample_agent.add_metadata("new_key", "new_value")
        
        assert sample_agent.metadata["new_key"] == "new_value"
        assert sample_agent.metadata["test"] == "data"  # Original metadata preserved
        assert sample_agent.updated_at > original_updated_at

    def test_to_dict(self, sample_agent):
        """Test converting agent to dictionary."""
        agent_dict = sample_agent.to_dict()
        
        assert agent_dict["id"] == str(sample_agent.id)
        assert agent_dict["name"] == sample_agent.name
        assert agent_dict["template_id"] == sample_agent.template_id
        assert agent_dict["template_version"] == sample_agent.template_version
        assert agent_dict["status"] == sample_agent.status.value
        assert agent_dict["metadata"] == sample_agent.metadata
        assert "configuration" in agent_dict
        assert "created_at" in agent_dict
        assert "updated_at" in agent_dict

    def test_from_dict(self, sample_agent):
        """Test creating agent from dictionary."""
        agent_dict = sample_agent.to_dict()
        restored_agent = Agent.from_dict(agent_dict)
        
        assert restored_agent.id == sample_agent.id
        assert restored_agent.name == sample_agent.name
        assert restored_agent.template_id == sample_agent.template_id
        assert restored_agent.template_version == sample_agent.template_version
        assert restored_agent.status == sample_agent.status
        assert restored_agent.metadata == sample_agent.metadata
        assert restored_agent.configuration.system_prompt == sample_agent.configuration.system_prompt

    def test_agent_equality_business_logic(self, sample_configuration):
        """Test agent equality based on ID (business logic)."""
        agent1 = Agent.create("Agent 1", "template-1", sample_configuration, agent_id="same-id")
        agent2 = Agent.create("Agent 2", "template-2", sample_configuration, agent_id="same-id")
        agent3 = Agent.create("Agent 3", "template-3", sample_configuration, agent_id="different-id")
        
        # Same ID = equal (business logic)
        assert agent1 == agent2
        # Different ID = not equal
        assert agent1 != agent3

"""Unit tests for CreateAgentCommand."""

import pytest

from runtime.application.commands.create_agent_command import CreateAgentCommand
from runtime.domain.value_objects.agent_configuration import AgentConfiguration


class TestCreateAgentCommand:
    """Test the CreateAgentCommand."""

    @pytest.fixture
    def sample_configuration(self):
        """Create sample agent configuration."""
        return AgentConfiguration(
            system_prompt="You are a helpful assistant",
            llm_config_id="gpt-4",
            conversation_config={"temperature": 0.7, "max_tokens": 1000},
            toolsets=["web_search", "calculator"],
            template_config={"setting": "value"}
        )

    def test_create_command_with_all_fields(self, sample_configuration):
        """Test creating command with all fields."""
        command = CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration,
            template_version="1.0.0",
            metadata={"test": "data"},
            agent_id="custom-agent-id"
        )

        assert command.name == "Test Agent"
        assert command.template_id == "test-template"
        assert command.configuration is sample_configuration
        assert command.template_version == "1.0.0"
        assert command.metadata == {"test": "data"}
        assert command.agent_id == "custom-agent-id"

    def test_create_command_with_minimal_fields(self, sample_configuration):
        """Test creating command with minimal required fields."""
        command = CreateAgentCommand(
            name="Minimal Agent",
            template_id="minimal-template",
            configuration=sample_configuration
        )

        assert command.name == "Minimal Agent"
        assert command.template_id == "minimal-template"
        assert command.configuration is sample_configuration
        assert command.template_version is None
        assert command.metadata is None
        assert command.agent_id is None

    def test_validation_empty_name(self, sample_configuration):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Agent name is required"):
            CreateAgentCommand(
                name="",
                template_id="test-template",
                configuration=sample_configuration
            )

    def test_validation_none_name(self, sample_configuration):
        """Test that None name raises ValueError."""
        with pytest.raises(ValueError, match="Agent name is required"):
            CreateAgentCommand(
                name=None,  # pyright: ignore[reportArgumentType]
                template_id="test-template",
                configuration=sample_configuration
            )

    def test_validation_empty_template_id(self, sample_configuration):
        """Test that empty template_id raises ValueError."""
        with pytest.raises(ValueError, match="Template ID is required"):
            CreateAgentCommand(
                name="Test Agent",
                template_id="",
                configuration=sample_configuration
            )

    def test_validation_none_template_id(self, sample_configuration):
        """Test that None template_id raises ValueError."""
        with pytest.raises(ValueError, match="Template ID is required"):
            CreateAgentCommand(
                name="Test Agent",
                template_id=None,  # pyright: ignore[reportArgumentType]
                configuration=sample_configuration
            )

    def test_validation_invalid_configuration(self):
        """Test that invalid configuration raises ValueError."""
        with pytest.raises(ValueError, match="Configuration must be an AgentConfiguration instance"):
            CreateAgentCommand(
                name="Test Agent",
                template_id="test-template",
                configuration={"invalid": "config"}  # Not AgentConfiguration  # pyright: ignore[reportArgumentType]
            )

    def test_validation_none_configuration(self):
        """Test that None configuration raises ValueError."""
        with pytest.raises(ValueError, match="Configuration must be an AgentConfiguration instance"):
            CreateAgentCommand(
                name="Test Agent",
                template_id="test-template",
                configuration=None  # pyright: ignore[reportArgumentType]
            )

    def test_validation_invalid_metadata(self, sample_configuration):
        """Test that invalid metadata raises ValueError."""
        with pytest.raises(ValueError, match="Metadata must be a dictionary"):
            CreateAgentCommand(
                name="Test Agent",
                template_id="test-template",
                configuration=sample_configuration,
                metadata="invalid_metadata"  # Not a dict  # pyright: ignore[reportArgumentType]
            )

    def test_get_template_configuration(self, sample_configuration):
        """Test getting template configuration."""
        command = CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration
        )

        template_config = command.get_template_configuration()

        # Should contain merged configuration from AgentConfiguration
        assert "system_prompt" in template_config
        assert "llm_config_id" in template_config
        assert "toolset_configs" in template_config
        assert "temperature" in template_config
        assert "max_tokens" in template_config
        assert "setting" in template_config

        # Verify values
        assert template_config["system_prompt"] == "You are a helpful assistant"
        assert template_config["llm_config_id"] == "gpt-4"
        assert template_config["toolset_configs"] == ["web_search", "calculator"]
        assert template_config["temperature"] == 0.7
        assert template_config["max_tokens"] == 1000
        assert template_config["setting"] == "value"

    def test_get_execution_params(self, sample_configuration):
        """Test getting execution parameters."""
        command = CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration
        )

        execution_params = command.get_execution_params()

        # Should contain only execution parameters
        assert execution_params == {"temperature": 0.7, "max_tokens": 1000}

    def test_get_execution_params_empty(self):
        """Test getting execution parameters with no conversation config."""
        config = AgentConfiguration()  # No conversation config
        command = CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=config
        )

        execution_params = command.get_execution_params()
        assert execution_params == {}

    def test_get_toolset_names(self, sample_configuration):
        """Test getting toolset names."""
        command = CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration
        )

        toolset_names = command.get_toolset_names()
        assert toolset_names == ["web_search", "calculator"]

    def test_get_toolset_names_empty(self):
        """Test getting toolset names with no toolsets."""
        config = AgentConfiguration()  # No toolsets
        command = CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=config
        )

        toolset_names = command.get_toolset_names()
        assert toolset_names == []


    def test_with_custom_agent_id(self, sample_configuration):
        """Test command with custom agent ID."""
        command = CreateAgentCommand(
            name="Custom ID Agent",
            template_id="test-template",
            configuration=sample_configuration,
            agent_id="my-custom-agent-id"
        )

        assert command.agent_id == "my-custom-agent-id"

    def test_with_complex_metadata(self, sample_configuration):
        """Test command with complex metadata."""
        complex_metadata = {
            "owner": "user-123",
            "tags": ["production", "customer-service"],
            "config": {
                "deployment": "us-west-2",
                "replicas": 3
            },
            "created_by": "admin",
            "version_info": {
                "major": 2,
                "minor": 1,
                "patch": 0
            }
        }

        command = CreateAgentCommand(
            name="Complex Agent",
            template_id="complex-template",
            configuration=sample_configuration,
            metadata=complex_metadata
        )

        assert command.metadata == complex_metadata
        # Ensure it's the same reference (not copied)
        assert command.metadata is complex_metadata

    def test_configuration_delegation(self, sample_configuration):
        """Test that configuration methods properly delegate to AgentConfiguration."""
        command = CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration
        )

        # All configuration methods should delegate to the configuration object
        assert command.get_template_configuration() == sample_configuration.get_template_configuration()
        assert command.get_execution_params() == sample_configuration.get_execution_params()
        assert command.get_toolset_names() == sample_configuration.get_toolset_names()


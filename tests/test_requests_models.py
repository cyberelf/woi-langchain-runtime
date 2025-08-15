"""Tests for request models and the new structured parsing functionality."""

import pytest
from pydantic import ValidationError

from runtime.infrastructure.web.models.requests import (
    CreateAgentRequest,
    AgentIdentityModel,
    AgentTemplateModel,
    AgentConfigurationModel,
)


class TestAgentIdentityModel:
    """Test the AgentIdentityModel."""

    def test_minimal_identity_model(self):
        """Test creating identity model with minimal required fields."""
        identity = AgentIdentityModel(id="test-agent-123", name="Test Agent")

        assert identity.id == "test-agent-123"
        assert identity.name == "Test Agent"
        assert identity.description is None
        assert identity.status == "draft"  # default value
        assert identity.version_type == "beta"  # default value
        assert identity.version_number == "v1"  # default value

    def test_full_identity_model(self):
        """Test creating identity model with all fields."""
        identity = AgentIdentityModel(
            id="test-agent-123",
            name="Test Agent",
            description="A test agent for validation",
            avatar_url="https://example.com/avatar.png",
            type="test",
            owner_id="user-456",
            status="active",
            agent_line_id="line-789",
            version_type="release",
            version_number="v2.1",
        )

        assert identity.id == "test-agent-123"
        assert identity.name == "Test Agent"
        assert identity.description == "A test agent for validation"
        assert identity.avatar_url == "https://example.com/avatar.png"
        assert identity.type == "test"
        assert identity.owner_id == "user-456"
        assert identity.status == "active"
        assert identity.agent_line_id == "line-789"
        assert identity.version_type == "release"
        assert identity.version_number == "v2.1"


class TestAgentTemplateModel:
    """Test the AgentTemplateModel."""

    def test_minimal_template_model(self):
        """Test creating template model with minimal required fields."""
        template = AgentTemplateModel(template_id="simple-test")

        assert template.template_id == "simple-test"
        assert template.template_version_id is None

    def test_template_model_with_version(self):
        """Test creating template model with version."""
        template = AgentTemplateModel(template_id="simple-test", template_version_id="1.0.0")

        assert template.template_id == "simple-test"
        assert template.template_version_id == "1.0.0"
        assert template.get_template_version() == "1.0.0"

    def test_template_model_with_version_id(self):
        """Test creating template model with version ID."""
        template = AgentTemplateModel(template_id="simple-test", template_version_id="v1.0.0-alpha")

        assert template.template_id == "simple-test"
        assert template.template_version_id == "v1.0.0-alpha"
        assert template.get_template_version() == "v1.0.0-alpha"


class TestAgentConfigurationModel:
    """Test the AgentConfigurationModel."""

    def test_empty_configuration_model(self):
        """Test creating configuration model with no fields."""
        config = AgentConfigurationModel()

        assert config.template_config is None
        assert config.system_prompt is None
        assert config.conversation_config is None
        assert config.toolsets is None
        assert config.llm_config_id is None

    def test_full_configuration_model(self):
        """Test creating configuration model with all fields."""
        config = AgentConfigurationModel(
            template_config={"template_setting": "value"},
            system_prompt="You are a helpful assistant",
            conversation_config={"max_history": 20},
            toolsets=["web_search", "calculator"],
            llm_config_id="openai-gpt4",
        )

        assert config.template_config == {"template_setting": "value"}
        assert config.system_prompt == "You are a helpful assistant"
        assert config.conversation_config == {"max_history": 20}
        assert config.toolsets == ["web_search", "calculator"]
        assert config.llm_config_id == "openai-gpt4"

    def test_get_configuration_basic(self):
        """Test that get_configuration returns template_config."""
        config = AgentConfigurationModel(
            template_config={"template_setting": "value", "other_setting": "value2"}
        )

        merged = config.get_configuration()

        assert merged["template_setting"] == "value"
        assert merged["other_setting"] == "value2"

    def test_get_configuration_camel_case_conversion(self):
        """Test that camelCase conversion works in nested conversation config."""
        config = AgentConfigurationModel(
            template_config={
                "conversation": {"historyLength": 15, "other_setting": "value"},
                "regular_setting": "value",
            }
        )

        merged = config.get_configuration()

        # historyLength should be converted to history_length and moved up
        assert merged["history_length"] == 15
        assert merged["other_setting"] == "value"
        assert merged["regular_setting"] == "value"
        assert "conversation" not in merged


class TestCreateAgentRequestParsing:
    """Test the new parsing functionality in CreateAgentRequest."""

    def test_create_agent_request_parsing(self):
        """Test that CreateAgentRequest correctly parses into structured models."""
        request = CreateAgentRequest(
            id="test-agent-123",
            name="Test Agent",
            description="A test agent",
            type="task",
            template_id="simple-test",
            template_version_id="1.0.0",
            template_config={"setting": "value"},
            system_prompt="You are helpful",
            agent_line_id="line-123",
            owner_id="user-456",
        )

        # Test identity parsing
        identity = request.get_identity()
        assert isinstance(identity, AgentIdentityModel)
        assert identity.id == "test-agent-123"
        assert identity.name == "Test Agent"
        assert identity.description == "A test agent"

        # Test template parsing
        template = request.get_template()
        assert isinstance(template, AgentTemplateModel)
        assert template.template_id == "simple-test"
        assert template.template_version_id == "1.0.0"

        # Test configuration parsing
        config = request.get_agent_configuration()
        assert isinstance(config, AgentConfigurationModel)
        assert config.template_config == {"setting": "value"}
        assert config.system_prompt == "You are helpful"

    def test_backward_compatibility(self):
        """Test that existing methods still work correctly."""
        request = CreateAgentRequest(
            id="test-agent-123",
            name="Test Agent",
            type="task",
            template_id="simple-test",
            template_version_id="v1.0.0-alpha",
            template_config={"setting": "value"},
            system_prompt="You are helpful",
            llm_config_id="openai-gpt4",
            agent_line_id="line-123",
            owner_id="user-456",
        )

        # Test existing methods work as before
        assert request.get_template_version() == "v1.0.0-alpha"  # version_id takes precedence

        merged_config = request.get_configuration()
        assert merged_config["setting"] == "value"

        metadata = request.get_metadata()
        assert metadata["system_prompt"] == "You are helpful"
        assert metadata["llm_config_id"] == "openai-gpt4"

    def test_create_agent_request_validation(self):
        """Test that CreateAgentRequest validation still works."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            CreateAgentRequest(name="Test Agent")  # missing required fields

        with pytest.raises(ValidationError):
            CreateAgentRequest(
                id="test", template_id="simple"
            )  # missing name, type, template_version_id, agent_line_id, owner_id

"""Unit tests for ComposeAgentService."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from runtime.application.services.compose_agent_service import ComposeAgentService
from runtime.domain.value_objects.template import TemplateInfo, ConfigField


class TestComposeAgentService:
    """Test the ComposeAgentService application service."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        mock_service = MagicMock()
        mock_client = AsyncMock()
        mock_service.get_client.return_value = mock_client
        return mock_service

    @pytest.fixture
    def mock_framework_executor(self):
        """Create mock framework executor."""
        mock_executor = MagicMock()
        
        # Mock toolset service
        mock_toolset_service = MagicMock()
        mock_toolset_service.get_all_toolset_names.return_value = [
            "web_search", "file_tools", "custom"
        ]
        mock_executor.get_toolset_service.return_value = mock_toolset_service
        
        return mock_executor

    @pytest.fixture
    def sample_template_info(self):
        """Create sample template info."""
        config_field = ConfigField.create_string_field(
            key="workflow_responsibility",
            description="The responsibility of the workflow agent",
            default=None
        )
        
        return TemplateInfo(
            id="test-template",
            name="Test Template",
            description="A template for testing",
            version="1.0.0",
            framework="langgraph",
            config_fields=[config_field]
        )

    @pytest.fixture
    def service(self, mock_llm_service, mock_framework_executor):
        """Create service instance with mocked dependencies."""
        return ComposeAgentService(mock_llm_service, mock_framework_executor)

    @pytest.mark.asyncio
    async def test_compose_success(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test successful agent composition."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        mock_framework_executor.validate_template_configuration.return_value = (True, None)
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "agent_id": "test-agent",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a test agent",
            "template_config": {"workflow_responsibility": "Testing"},
            "toolsets": ["web_search"],
            "reasoning": "This is a test configuration"
        })
        
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.return_value = mock_response
        
        # Execute
        result = await service.compose(
            template_id="test-template",
            instructions="Create a test agent",
            llm_config_id="gpt-4"
        )
        
        # Assert
        assert result["agent_id"] == "test-agent"
        assert result["name"] == "Test Agent"
        assert result["description"] == "A test agent"
        assert result["system_prompt"] == "You are a test agent"
        assert result["template_config"] == {"workflow_responsibility": "Testing"}
        assert result["toolsets"] == ["web_search"]
        assert result["template_id"] == "test-template"
        assert result["template_version_id"] == "1.0.0"
        
        # Verify LLM was called
        mock_client.ainvoke.assert_called_once()
        
        # Verify validation was called
        mock_framework_executor.validate_template_configuration.assert_called_once_with(
            "test-template",
            {"workflow_responsibility": "Testing"}
        )

    @pytest.mark.asyncio
    async def test_compose_with_json_code_block(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test composition with LLM response wrapped in JSON code block."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        mock_framework_executor.validate_template_configuration.return_value = (True, None)
        
        # Mock LLM response with code block
        config_dict = {
            "agent_id": "test-agent",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a test agent",
            "template_config": {"workflow_responsibility": "Testing"},
            "toolsets": []
        }
        mock_response = MagicMock()
        mock_response.content = f"```json\n{json.dumps(config_dict)}\n```"
        
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.return_value = mock_response
        
        # Execute
        result = await service.compose(
            template_id="test-template",
            instructions="Create a test agent"
        )
        
        # Assert
        assert result["agent_id"] == "test-agent"
        assert result["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_compose_with_validation_warning(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test composition with validation failure (returns warning)."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        
        # Mock validation failure
        from pydantic import ValidationError
        validation_error = MagicMock(spec=ValidationError)
        mock_framework_executor.validate_template_configuration.return_value = (
            False, 
            validation_error
        )
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "agent_id": "test-agent",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a test agent",
            "template_config": {"invalid_field": "value"},
            "toolsets": []
        })
        
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.return_value = mock_response
        
        # Execute
        result = await service.compose(
            template_id="test-template",
            instructions="Create a test agent"
        )
        
        # Assert - should return with warning
        assert result["agent_id"] == "test-agent"
        assert "validation_warning" in result
        assert result["validation_warning"] == validation_error

    @pytest.mark.asyncio
    async def test_compose_template_not_found(
        self, service, mock_framework_executor
    ):
        """Test composition with non-existent template."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = []
        
        # Execute and assert
        with pytest.raises(ValueError, match="Template 'non-existent' not found"):
            await service.compose(
                template_id="non-existent",
                instructions="Create a test agent"
            )

    @pytest.mark.asyncio
    async def test_compose_missing_required_fields(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test composition with LLM response missing required fields."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        
        # Mock LLM response with missing fields
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "agent_id": "test-agent",
            # Missing: name, description, system_prompt, template_config
        })
        
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.return_value = mock_response
        
        # Execute and assert
        with pytest.raises(ValueError, match="Missing required fields"):
            await service.compose(
                template_id="test-template",
                instructions="Create a test agent"
            )

    @pytest.mark.asyncio
    async def test_compose_invalid_json(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test composition with invalid JSON response."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        
        # Mock LLM response with invalid JSON
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON {{"
        
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.return_value = mock_response
        
        # Execute and assert
        with pytest.raises(ValueError, match="Could not parse LLM response as JSON"):
            await service.compose(
                template_id="test-template",
                instructions="Create a test agent"
            )

    @pytest.mark.asyncio
    async def test_compose_with_suggested_name_and_tools(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test composition with suggested name and tools."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        mock_framework_executor.validate_template_configuration.return_value = (True, None)
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "agent_id": "test-agent",
            "name": "Suggested Agent Name",
            "description": "A test agent",
            "system_prompt": "You are a test agent",
            "template_config": {"workflow_responsibility": "Testing"},
            "toolsets": ["web_search", "file_tools"]
        })
        
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.return_value = mock_response
        
        # Execute
        result = await service.compose(
            template_id="test-template",
            instructions="Create a test agent",
            suggested_name="My Custom Agent",
            suggested_tools=["web_search", "file_tools"]
        )
        
        # Assert
        assert result["name"] == "Suggested Agent Name"
        assert result["toolsets"] == ["web_search", "file_tools"]
        
        # Verify the user prompt included suggestions
        call_args = mock_client.ainvoke.call_args[0][0]
        user_message = call_args[1].content
        assert "Suggested Name: My Custom Agent" in user_message
        assert "Suggested Tools: web_search, file_tools" in user_message

    @pytest.mark.asyncio
    async def test_compose_llm_exception(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test composition when LLM call raises an exception."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        
        # Mock LLM to raise exception
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.side_effect = Exception("LLM API error")
        
        # Execute and assert
        with pytest.raises(ValueError, match="Agent composition failed: LLM API error"):
            await service.compose(
                template_id="test-template",
                instructions="Create a test agent"
            )

    @pytest.mark.asyncio
    async def test_compose_with_list_response_content(
        self, service, mock_llm_service, mock_framework_executor, sample_template_info
    ):
        """Test composition when LLM returns content as a list."""
        # Setup mocks
        mock_framework_executor.get_templates.return_value = [sample_template_info]
        mock_framework_executor.validate_template_configuration.return_value = (True, None)
        
        # Mock LLM response with list content
        config_dict = {
            "agent_id": "test-agent",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a test agent",
            "template_config": {"workflow_responsibility": "Testing"},
            "toolsets": []
        }
        mock_response = MagicMock()
        mock_response.content = [json.dumps(config_dict)]
        
        mock_client = mock_llm_service.get_client.return_value
        mock_client.ainvoke.return_value = mock_response
        
        # Execute
        result = await service.compose(
            template_id="test-template",
            instructions="Create a test agent"
        )
        
        # Assert
        assert result["agent_id"] == "test-agent"
        assert result["name"] == "Test Agent"

    def test_build_system_prompt(self, service, sample_template_info, mock_framework_executor):
        """Test system prompt building."""
        # Setup mock
        mock_toolset_service = MagicMock()
        mock_toolset_service.get_all_toolset_names.return_value = ["tool1", "tool2"]
        mock_framework_executor.get_toolset_service.return_value = mock_toolset_service
        
        # Execute
        prompt = service._build_system_prompt(sample_template_info)
        
        # Assert
        assert "test-template" in prompt.lower() or "Test Template" in prompt
        assert "workflow_responsibility" in prompt
        assert "tool1" in prompt
        assert "tool2" in prompt
        assert "JSON" in prompt

    def test_build_system_prompt_no_toolset_service(
        self, service, sample_template_info, mock_framework_executor
    ):
        """Test system prompt building when toolset service is None."""
        # Setup mock
        mock_framework_executor.get_toolset_service.return_value = None
        
        # Execute
        prompt = service._build_system_prompt(sample_template_info)
        
        # Assert - should not raise an error
        assert "Test Template" in prompt
        assert "Available Tools: " in prompt

    def test_build_user_prompt(self, service):
        """Test user prompt building."""
        # Execute
        prompt = service._build_user_prompt(
            instructions="Create an agent for data analysis",
            suggested_name="DataBot",
            suggested_tools=["web_search", "calculator"]
        )
        
        # Assert
        assert "Create an agent for data analysis" in prompt
        assert "Suggested Name: DataBot" in prompt
        assert "Suggested Tools: web_search, calculator" in prompt
        assert "Generate the agent configuration as JSON" in prompt

    def test_parse_llm_response_valid(self, service):
        """Test parsing valid LLM response."""
        # Prepare response
        config = {
            "agent_id": "test-agent",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a test agent",
            "template_config": {"key": "value"}
        }
        response_text = json.dumps(config)
        
        # Execute
        result = service._parse_llm_response(response_text, "test-template")
        
        # Assert
        assert result["agent_id"] == "test-agent"
        assert result["template_id"] == "test-template"
        assert result["template_version_id"] == "1.0.0"
        assert result["toolsets"] == []  # Default
        assert "reasoning" in result  # Default

    def test_parse_llm_response_with_code_block(self, service):
        """Test parsing LLM response with code block."""
        # Prepare response
        config = {
            "agent_id": "test-agent",
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a test agent",
            "template_config": {"key": "value"}
        }
        response_text = f"```json\n{json.dumps(config)}\n```"
        
        # Execute
        result = service._parse_llm_response(response_text, "test-template")
        
        # Assert
        assert result["agent_id"] == "test-agent"

    def test_parse_llm_response_missing_fields(self, service):
        """Test parsing LLM response with missing required fields."""
        # Prepare response with missing fields
        config = {
            "agent_id": "test-agent"
            # Missing: name, description, system_prompt, template_config
        }
        response_text = json.dumps(config)
        
        # Execute and assert
        with pytest.raises(ValueError, match="Missing required fields"):
            service._parse_llm_response(response_text, "test-template")

    def test_parse_llm_response_invalid_json(self, service):
        """Test parsing invalid JSON response."""
        # Prepare invalid response
        response_text = "This is not JSON"
        
        # Execute and assert
        with pytest.raises(ValueError, match="Could not parse LLM response as JSON"):
            service._parse_llm_response(response_text, "test-template")


"""Unit tests for CreateAgentService."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from runtime.application.services.create_agent_service import CreateAgentService
from runtime.application.commands.create_agent_command import CreateAgentCommand
from runtime.domain.entities.agent import Agent, AgentStatus
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.domain.events.domain_events import AgentCreated


class TestCreateAgentService:
    """Test the CreateAgentService application service."""

    @pytest.fixture
    def mock_uow(self):
        """Create mock unit of work."""
        mock_uow = AsyncMock()
        mock_uow.agents = AsyncMock()
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)
        return mock_uow

    @pytest.fixture
    def mock_template_validator(self):
        """Create mock template validator."""
        mock_validator = MagicMock()
        mock_validator.template_exists.return_value = True
        mock_validator.validate_template_configuration.return_value = (True, None)
        return mock_validator

    @pytest.fixture
    def service(self, mock_uow, mock_template_validator):
        """Create service instance with mocked dependencies."""
        return CreateAgentService(mock_uow, mock_template_validator)

    @pytest.fixture
    def sample_configuration(self):
        """Create sample agent configuration."""
        return AgentConfiguration(
            system_prompt="You are a helpful assistant",
            llm_config_id="gpt-4",
            conversation_config={"temperature": 0.7, "max_tokens": 1000},
            toolsets=["web_search"],
            template_config={"setting": "value"}
        )

    @pytest.fixture
    def sample_command(self, sample_configuration):
        """Create sample create agent command."""
        return CreateAgentCommand(
            name="Test Agent",
            template_id="test-template",
            configuration=sample_configuration,
            template_version="1.0.0",
            metadata={"test": "data"},
            agent_id=f"test-agent-{uuid.uuid4()}"
        )

    @pytest.mark.asyncio
    async def test_execute_successful_creation(self, service, sample_command, mock_uow, mock_template_validator):
        """Test successful agent creation."""
        # Setup mocks
        mock_uow.agents.get_by_name.return_value = None  # No existing agent
        mock_uow.agents.get_by_id.return_value = None  # No existing agent
        
        with patch('runtime.domain.services.agent_validation_service.AgentValidationService') as mock_validation_service:
            mock_validation_service.return_value.validate_agent_configuration.return_value = []
            
            # Execute
            result = await service.execute(sample_command)
            
            # Verify result
            assert isinstance(result, Agent)
            assert result.name == "Test Agent"
            assert result.template_id == "test-template"
            assert result.status == AgentStatus.CREATED
            assert str(result.id) == sample_command.agent_id
            
            # Verify interactions
            mock_template_validator.template_exists.assert_called_once_with("test-template")
            mock_template_validator.validate_template_configuration.assert_called_once()
            mock_uow.agents.get_by_name.assert_called_once_with("Test Agent")
            mock_uow.agents.save.assert_called_once()
            mock_uow.commit.assert_called_once()
            
            # Verify domain event was raised
            events = service.get_events()
            assert len(events) == 1
            assert isinstance(events[0], AgentCreated)

    @pytest.mark.asyncio
    async def test_execute_template_not_found(self, service, sample_command, mock_template_validator):
        """Test failure when template doesn't exist."""
        # Setup mock to return template not found
        mock_template_validator.template_exists.return_value = False
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Template 'test-template' not found"):
            await service.execute(sample_command)
        
        # Verify template validation was called
        mock_template_validator.template_exists.assert_called_once_with("test-template")

    @pytest.mark.asyncio
    async def test_execute_template_configuration_validation_failed(self, service, sample_command, mock_template_validator):
        """Test failure when template configuration is invalid."""
        # Setup mock to return validation failure
        mock_template_validator.validate_template_configuration.return_value = (False, "Invalid config")
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Template configuration validation failed: Invalid config"):
            await service.execute(sample_command)
        
        # Verify validation was called
        mock_template_validator.template_exists.assert_called_once_with("test-template")
        mock_template_validator.validate_template_configuration.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_duplicate_agent_name(self, service, sample_command, mock_uow):
        """Test failure when agent name already exists."""
        # Setup existing agent
        existing_agent = Agent.create(
            name="Test Agent",
            template_id="other-template",
            configuration=sample_command.configuration
        )
        mock_uow.agents.get_by_name.return_value = existing_agent
        mock_uow.agents.get_by_id.return_value = None
        
        with patch('runtime.domain.services.agent_validation_service.AgentValidationService') as mock_validation_service:
            mock_validation_service.return_value.validate_agent_configuration.return_value = []
            
            # Execute and verify exception
            with pytest.raises(ValueError, match="Agent with name 'Test Agent' already exists"):
                await service.execute(sample_command)
            
            # Verify uniqueness check was performed
            mock_uow.agents.get_by_name.assert_called_once_with("Test Agent")

    @pytest.mark.asyncio
    async def test_execute_database_error_rollback(self, service, sample_command, mock_uow, mock_template_validator):
        """Test that database errors trigger rollback."""
        mock_uow.agents.get_by_name.return_value = None
        mock_uow.agents.get_by_id.return_value = None

        # Simulate database error during save
        mock_uow.agents.save.side_effect = Exception("Database error")
        
        with patch('runtime.domain.services.agent_validation_service.AgentValidationService') as mock_validation_service:
            mock_validation_service.return_value.validate_agent_configuration.return_value = []
            
            # Execute and verify exception propagates
            with pytest.raises(Exception, match="Database error"):
                await service.execute(sample_command)
            
            # Verify rollback was called
            mock_uow.rollback.assert_called_once()
            mock_uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_generated_agent_id(self, service, mock_uow, mock_template_validator, sample_configuration):
        """Test agent creation with generated ID (no agent_id provided)."""
        command = CreateAgentCommand(
            name="Auto ID Agent",
            template_id="test-template",
            configuration=sample_configuration
        )
        
        mock_uow.agents.get_by_name.return_value = None
        
        with patch('runtime.domain.services.agent_validation_service.AgentValidationService') as mock_validation_service:
            mock_validation_service.return_value.validate_agent_configuration.return_value = []
            
            # Execute
            result = await service.execute(command)
            
            # Verify ID was generated (not None and not empty)
            assert result.id is not None
            assert str(result.id) != ""
            
            # Verify other properties
            assert result.name == "Auto ID Agent"

    def test_get_events_returns_copy(self, service):
        """Test that get_events returns a copy, not the original list."""
        # Add some mock events
        service._events.append("event1")
        service._events.append("event2")
        
        events = service.get_events()
        
        # Modify returned list
        events.append("event3")
        
        # Original should be unchanged
        assert len(service._events) == 2
        assert len(events) == 3

    def test_clear_events(self, service):
        """Test clearing domain events."""
        # Add some mock events
        service._events.append("event1")
        service._events.append("event2")
        
        assert len(service._events) == 2
        
        service.clear_events()
        
        assert len(service._events) == 0

    @pytest.mark.asyncio
    async def test_logging_info_messages(self, service, sample_command, mock_uow, mock_template_validator):
        """Test that info logging messages are generated."""
        mock_uow.agents.get_by_name.return_value = None
        mock_uow.agents.get_by_id.return_value = None
        
        with patch('runtime.domain.services.agent_validation_service.AgentValidationService') as mock_validation_service:
            mock_validation_service.return_value.validate_agent_configuration.return_value = []
            
            with patch('runtime.application.services.create_agent_service.logger') as mock_logger:
                await service.execute(sample_command)
                
                # Verify logging calls
                mock_logger.info.assert_any_call("Creating agent: Test Agent")
                assert mock_logger.info.call_count >= 2  # At least start and success messages

    @pytest.mark.asyncio
    async def test_logging_error_messages(self, service, sample_command, mock_uow, mock_template_validator):
        """Test that error logging messages are generated on failure."""
        mock_uow.agents.get_by_name.return_value = None
        mock_uow.agents.save.side_effect = Exception("Database error")
        
        with patch('runtime.domain.services.agent_validation_service.AgentValidationService') as mock_validation_service:
            mock_validation_service.return_value.validate_agent_configuration.return_value = []
            
            with patch('runtime.application.services.create_agent_service.logger') as mock_logger:
                with pytest.raises(Exception):
                    await service.execute(sample_command)
                
                # Verify error logging
                mock_logger.error.assert_called_once()
                assert "Failed to create agent" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_template_configuration_passed_correctly(self, service, sample_command, mock_uow, mock_template_validator):
        """Test that template configuration is correctly passed to validator."""
        mock_uow.agents.get_by_name.return_value = None
        mock_uow.agents.get_by_id.return_value = None

        with patch('runtime.domain.services.agent_validation_service.AgentValidationService') as mock_validation_service:
            mock_validation_service.return_value.validate_agent_configuration.return_value = []
            
            await service.execute(sample_command)
            
            # Verify template configuration was passed correctly
            call_args = mock_template_validator.validate_template_configuration.call_args
            assert call_args[0][0] == "test-template"
            
            # Should contain merged configuration
            config_dict = call_args[0][1]
            assert "system_prompt" in config_dict
            assert "temperature" in config_dict
            assert "toolset_configs" in config_dict

    def test_service_initialization(self, mock_uow, mock_template_validator):
        """Test service initialization."""
        service = CreateAgentService(mock_uow, mock_template_validator)
        
        assert service.uow is mock_uow
        assert service.template_validator is mock_template_validator
        assert service.validation_service is not None
        assert service._events == []

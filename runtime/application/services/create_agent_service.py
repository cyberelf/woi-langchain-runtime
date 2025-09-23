"""Create agent application service - Use case implementation."""

import logging

from ...domain.entities.agent import Agent
from ...domain.services.agent_validation_service import AgentValidationService
from ...domain.services.template_validation_service import TemplateValidationInterface
from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ...domain.events.domain_events import AgentCreated
from ..commands.create_agent_command import CreateAgentCommand

logger = logging.getLogger(__name__)


class CreateAgentService:
    """Application service for creating agents.
    
    Orchestrates the agent creation use case. Manages transaction boundaries
    and coordinates domain objects to fulfill the business requirement.
    """
    
    def __init__(self, uow: UnitOfWorkInterface, template_validator: TemplateValidationInterface):
        self.uow = uow
        self.template_validator = template_validator
        self.validation_service = AgentValidationService()
        self._events: list[object] = []
    
    async def execute(self, command: CreateAgentCommand) -> Agent:
        """Execute the create agent use case.
        
        This method represents the complete business transaction for
        creating a new agent.
        """
        logger.info(f"Creating agent: {command.name}")
        
        async with self.uow:
            try:
                # 1. Validate template exists
                if not self.template_validator.template_exists(command.template_id):
                    raise ValueError(f"Template '{command.template_id}' not found")
                
                # 2. Validate template configuration
                config_dict = command.configuration.get_template_configuration()
                is_valid, validation_error = self.template_validator.validate_template_configuration(
                    command.template_id, 
                    config_dict
                )
                if not is_valid:
                    raise ValueError(f"Template configuration validation failed: {validation_error}")
                
                # 3. Create domain entity
                agent = Agent.create(
                    name=command.name,
                    template_id=command.template_id,
                    configuration=command.configuration,
                    template_version=command.template_version,
                    metadata=command.metadata,
                    agent_id=command.agent_id
                )
                
                # 4. Validate cross-cutting business rules
                validation_errors = self.validation_service.validate_agent_configuration(agent)
                if validation_errors:
                    raise ValueError(f"Agent validation failed: {', '.join(validation_errors)}")
                
                # 5. Check uniqueness constraint
                existing_agent = await self.uow.agents.get_by_name(command.name)
                if existing_agent:
                    raise ValueError(f"Agent with name '{command.name}' already exists")
                
                # 6. Save to repository
                await self.uow.agents.save(agent)
                
                # 7. Raise domain event
                event = AgentCreated.create(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    template_id=agent.template_id
                )
                self._events.append(event)
                
                # 8. Commit transaction
                await self.uow.commit()
                
                logger.info(f"Successfully created agent: {agent.id}")
                return agent
                
            except Exception as e:
                logger.error(f"Failed to create agent: {e}")
                await self.uow.rollback()
                raise
    
    def get_events(self) -> list[object]:
        """Get domain events raised during execution."""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear domain events."""
        self._events.clear()
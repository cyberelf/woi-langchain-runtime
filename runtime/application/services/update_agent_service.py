"""Update agent service - Application layer."""

import logging
from typing import Optional

from ...domain.entities.agent import Agent
from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ..commands.update_agent_command import UpdateAgentCommand

logger = logging.getLogger(__name__)


class UpdateAgentService:
    """Service for updating existing agents."""
    
    def __init__(self, uow: UnitOfWorkInterface):
        """Initialize the service with unit of work."""
        self.uow = uow
    
    async def execute(self, command: UpdateAgentCommand) -> Agent:
        """Execute the update agent command.
        
        Args:
            command: The update command containing agent ID and new values
            
        Returns:
            Updated agent entity
            
        Raises:
            ValueError: If agent not found or validation fails
        """
        async with self.uow:
            # Get existing agent
            agent = await self.uow.agents.get_by_id(command.agent_id)
            if not agent:
                raise ValueError(f"Agent {command.agent_id.value} not found")
            
            # Track original values for logging
            original_name = agent.name
            original_template = agent.template_id
            
            # Update fields if provided (following KISS principle - simple field updates)
            updated = False
            
            if command.name is not None:
                agent.name = command.name
                updated = True
            
            if command.template_id is not None:
                agent.template_id = command.template_id
                updated = True
            
            if command.template_version is not None:
                agent.template_version = command.template_version
                updated = True
            
            if command.configuration is not None:
                agent.configuration = command.configuration
                updated = True
            
            if command.metadata is not None:
                agent.metadata = command.metadata or {}
                updated = True
            
            if not updated:
                logger.info(f"No changes requested for agent {command.agent_id.value}")
                return agent
            
            # Update the agent in repository
            await self.uow.agents.update(agent)
            await self.uow.commit()
            
            logger.info(
                f"Updated agent {command.agent_id.value}: "
                f"name '{original_name}' -> '{agent.name}', "
                f"template '{original_template}' -> '{agent.template_id}'"
            )
            
            return agent


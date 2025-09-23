"""Update agent status service - Application layer."""

import logging
from datetime import datetime, UTC

from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ...domain.entities.agent import Agent
from ..commands.update_agent_status_command import UpdateAgentStatusCommand

logger = logging.getLogger(__name__)


class UpdateAgentStatusService:
    """Service for updating agent status."""
    
    def __init__(self, uow: UnitOfWorkInterface):
        """Initialize the update agent status service.
        
        Args:
            uow: Unit of work for transaction management
        """
        self._uow = uow
    
    async def execute(self, command: UpdateAgentStatusCommand) -> Agent:
        """Execute the update agent status command.
        
        Args:
            command: Update agent status command
            
        Returns:
            Updated agent entity
            
        Raises:
            ValueError: If agent not found or validation fails
        """
        async with self._uow:
            # Get the existing agent
            agent = await self._uow.agents.get_by_id(command.agent_id)
            if not agent:
                raise ValueError(f"Agent {command.agent_id.value} not found")
            
            # Update the status
            updated_agent = agent.update_status(command.status)
            
            # Save the updated agent
            await self._uow.agents.update(updated_agent)
            
            # Commit the transaction
            await self._uow.commit()
            
            logger.info(f"Agent {command.agent_id.value} status updated to {command.status.value}")
            return updated_agent


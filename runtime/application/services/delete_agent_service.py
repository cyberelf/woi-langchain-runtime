"""Delete agent service - Application layer."""

import logging
from typing import Optional

from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ...domain.entities.agent import Agent
from ..commands.delete_agent_command import DeleteAgentCommand

logger = logging.getLogger(__name__)


class DeleteAgentService:
    """Service for deleting agents."""
    
    def __init__(self, uow: UnitOfWorkInterface):
        """Initialize the delete agent service.
        
        Args:
            uow: Unit of work for transaction management
        """
        self._uow = uow
    
    async def execute(self, command: DeleteAgentCommand) -> bool:
        """Execute the delete agent command.
        
        Args:
            command: Delete agent command
            
        Returns:
            True if agent was deleted successfully
            
        Raises:
            ValueError: If agent not found or validation fails
        """
        async with self._uow:
            # Check if agent exists
            agent = await self._uow.agents.get_by_id(command.agent_id)
            if not agent:
                raise ValueError(f"Agent {command.agent_id.value} not found")
            
            # Delete the agent
            await self._uow.agents.delete(command.agent_id)
            
            # Commit the transaction
            await self._uow.commit()
            
            logger.info(f"Agent {command.agent_id.value} deleted successfully")
            return True


"""Query agent application service - Read use cases."""

import logging
from typing import List, Optional

from ...domain.entities.agent import Agent
from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ..queries.get_agent_query import GetAgentQuery, ListAgentsQuery

logger = logging.getLogger(__name__)


class QueryAgentService:
    """Application service for querying agents.
    
    Handles read-only use cases for agent information.
    No transaction boundaries needed for read operations.
    """
    
    def __init__(self, uow: UnitOfWorkInterface):
        self.uow = uow
    
    async def get_agent(self, query: GetAgentQuery) -> Optional[Agent]:
        """Get a single agent by ID."""
        logger.debug(f"Getting agent: {query.agent_id}")
        
        # No transaction needed for read operation
        return await self.uow.agents.get_by_id(query.agent_id)
    
    async def list_agents(self, query: ListAgentsQuery) -> List[Agent]:
        """List agents with optional filtering."""
        logger.debug(f"Listing agents with filter: template_id={query.template_id}, active_only={query.active_only}")
        
        # Apply filtering based on query parameters
        if query.template_id and query.active_only:
            # Get active agents for specific template
            all_template_agents = await self.uow.agents.list_by_template(query.template_id)
            agents = [agent for agent in all_template_agents if agent.is_active()]
        elif query.template_id:
            # Get all agents for specific template
            agents = await self.uow.agents.list_by_template(query.template_id)
        elif query.active_only:
            # Get all active agents
            agents = await self.uow.agents.list_active()
        else:
            # Get all agents
            agents = await self.uow.agents.list_all()
        
        # Apply pagination
        start_idx = query.offset
        if query.limit:
            end_idx = start_idx + query.limit
            agents = agents[start_idx:end_idx]
        elif query.offset > 0:
            agents = agents[start_idx:]
        
        return agents
    
    async def agent_exists(self, agent_id) -> bool:
        """Check if agent exists."""
        from ...domain.value_objects.agent_id import AgentId
        if isinstance(agent_id, str):
            agent_id = AgentId.from_string(agent_id)
        
        return await self.uow.agents.exists(agent_id)
    
    async def get_agent_count(self) -> int:
        """Get total agent count."""
        return await self.uow.agents.count()
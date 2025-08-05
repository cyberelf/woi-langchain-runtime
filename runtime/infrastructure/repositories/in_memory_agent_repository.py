"""In-memory agent repository implementation - Infrastructure layer."""

from typing import Dict, List, Optional

from ...domain.entities.agent import Agent, AgentStatus
from ...domain.repositories.agent_repository import AgentRepositoryInterface
from ...domain.value_objects.agent_id import AgentId


class InMemoryAgentRepository(AgentRepositoryInterface):
    """In-memory implementation of agent repository.
    
    Infrastructure layer implementation that provides concrete
    persistence for domain entities using in-memory storage.
    """
    
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
    
    async def save(self, agent: Agent) -> None:
        """Save an agent."""
        self._agents[agent.id.value] = agent
    
    async def get_by_id(self, agent_id: AgentId) -> Optional[Agent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id.value)
    
    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Get an agent by name."""
        for agent in self._agents.values():
            if agent.name == name:
                return agent
        return None
    
    async def list_all(self) -> List[Agent]:
        """List all agents."""
        return list(self._agents.values())
    
    async def list_by_template(self, template_id: str) -> List[Agent]:
        """List agents by template ID."""
        return [
            agent for agent in self._agents.values()
            if agent.template_id == template_id
        ]
    
    async def list_active(self) -> List[Agent]:
        """List active agents."""
        return [
            agent for agent in self._agents.values()
            if agent.status == AgentStatus.ACTIVE
        ]
    
    async def exists(self, agent_id: AgentId) -> bool:
        """Check if agent exists."""
        return agent_id.value in self._agents
    
    async def delete(self, agent_id: AgentId) -> bool:
        """Delete an agent."""
        if agent_id.value in self._agents:
            del self._agents[agent_id.value]
            return True
        return False
    
    async def count(self) -> int:
        """Count total agents."""
        return len(self._agents)
    
    def clear(self) -> None:
        """Clear all agents (for testing)."""
        self._agents.clear()
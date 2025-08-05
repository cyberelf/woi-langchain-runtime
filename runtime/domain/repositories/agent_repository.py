"""Agent repository interface - Pure domain contract."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.agent import Agent
from ..value_objects.agent_id import AgentId


class AgentRepositoryInterface(ABC):
    """Repository interface for Agent entities.
    
    This interface defines the contract for agent persistence without
    specifying implementation details. Pure domain interface.
    """
    
    @abstractmethod
    async def save(self, agent: Agent) -> None:
        """Save an agent."""
        pass
    
    @abstractmethod
    async def get_by_id(self, agent_id: AgentId) -> Optional[Agent]:
        """Get an agent by ID."""
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Get an agent by name."""
        pass
    
    @abstractmethod
    async def list_all(self) -> List[Agent]:
        """List all agents."""
        pass
    
    @abstractmethod
    async def list_by_template(self, template_id: str) -> List[Agent]:
        """List agents by template ID."""
        pass
    
    @abstractmethod
    async def list_active(self) -> List[Agent]:
        """List active agents."""
        pass
    
    @abstractmethod
    async def exists(self, agent_id: AgentId) -> bool:
        """Check if agent exists."""
        pass
    
    @abstractmethod
    async def delete(self, agent_id: AgentId) -> bool:
        """Delete an agent."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Count total agents."""
        pass
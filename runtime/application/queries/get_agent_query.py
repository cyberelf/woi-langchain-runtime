"""Get agent query - Application layer."""

from dataclasses import dataclass
from typing import Optional

from ...domain.value_objects.agent_id import AgentId


@dataclass(frozen=True)
class GetAgentQuery:
    """Query to get an agent by ID.
    
    Represents the intent to retrieve agent information.
    """
    
    agent_id: AgentId
    
    def __post_init__(self):
        """Validate query data."""
        if not isinstance(self.agent_id, AgentId):
            raise ValueError("Agent ID must be an AgentId object")


@dataclass(frozen=True)
class ListAgentsQuery:
    """Query to list agents with optional filtering.
    
    Represents the intent to retrieve multiple agents.
    """
    
    template_id: Optional[str] = None
    active_only: bool = False
    limit: Optional[int] = None
    offset: int = 0
    
    def __post_init__(self):
        """Validate query data."""
        if self.limit is not None and self.limit <= 0:
            raise ValueError("Limit must be positive")
        if self.offset < 0:
            raise ValueError("Offset must be non-negative")
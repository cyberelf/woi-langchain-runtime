"""Update agent status command - Application layer."""

from pydantic import BaseModel, Field

from ...domain.value_objects.agent_id import AgentId
from ...domain.entities.agent import AgentStatus


class UpdateAgentStatusCommand(BaseModel):
    """Command to update an agent's status."""
    
    agent_id: AgentId = Field(..., description="ID of the agent to update")
    status: AgentStatus = Field(..., description="New status for the agent")
    
    class Config:
        arbitrary_types_allowed = True


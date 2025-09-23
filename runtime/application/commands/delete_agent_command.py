"""Delete agent command - Application layer."""

from pydantic import BaseModel, Field

from ...domain.value_objects.agent_id import AgentId


class DeleteAgentCommand(BaseModel):
    """Command to delete an agent."""
    
    agent_id: AgentId = Field(..., description="ID of the agent to delete")
    
    class Config:
        arbitrary_types_allowed = True


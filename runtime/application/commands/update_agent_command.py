"""Update agent command - Application layer."""

from typing import Optional, Any
from pydantic import BaseModel, Field

from ...domain.value_objects.agent_id import AgentId
from ...domain.value_objects.agent_configuration import AgentConfiguration


class UpdateAgentCommand(BaseModel):
    """Command to update an existing agent."""
    
    agent_id: AgentId = Field(..., description="ID of the agent to update")
    name: Optional[str] = Field(None, description="New name for the agent")
    template_id: Optional[str] = Field(None, description="New template ID")
    template_version: Optional[str] = Field(None, description="New template version")
    configuration: Optional[AgentConfiguration] = Field(None, description="New agent configuration")
    metadata: Optional[dict[str, Any]] = Field(None, description="New metadata")
    
    class Config:
        arbitrary_types_allowed = True


"""Additional agent request models - Infrastructure layer."""

from typing import Optional, Any
from pydantic import BaseModel, Field

from ....domain.value_objects.agent_configuration import AgentConfiguration


class UpdateAgentRequest(BaseModel):
    """Request to update an agent."""
    
    name: Optional[str] = Field(None, description="New name for the agent")
    template_id: Optional[str] = Field(None, description="New template ID")
    template_version: Optional[str] = Field(None, description="New template version")
    configuration: Optional[dict[str, Any]] = Field(None, description="New agent configuration")
    metadata: Optional[dict[str, Any]] = Field(None, description="New metadata")
    
    def get_agent_configuration(self) -> Optional[AgentConfiguration]:
        """Convert configuration dict to AgentConfiguration if provided."""
        if self.configuration:
            return AgentConfiguration.from_dict(self.configuration)
        return None


class UpdateAgentStatusRequest(BaseModel):
    """Request to update an agent's status."""
    
    status: str = Field(..., description="New status (active, inactive, archived)")
    
    def get_status(self) -> "AgentStatus":
        """Convert status string to AgentStatus enum."""
        from ....domain.entities.agent import AgentStatus
        return AgentStatus(self.status)


"""Create agent command - Application layer."""

from dataclasses import dataclass
from typing import Optional, Any

from ...domain.value_objects.agent_configuration import AgentConfiguration


@dataclass(frozen=True)
class CreateAgentCommand:
    """Command to create a new agent.
    
    Represents the intent to create a new agent in the system.
    Uses domain AgentConfiguration for type safety and validation.
    """
    
    name: str
    template_id: str
    configuration: AgentConfiguration
    template_version: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    agent_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate command data."""
        if not self.name:
            raise ValueError("Agent name is required")
        if not self.template_id:
            raise ValueError("Template ID is required")
        if not isinstance(self.configuration, AgentConfiguration):
            raise ValueError("Configuration must be an AgentConfiguration instance")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
    
    def get_template_configuration(self) -> dict[str, Any]:
        """Get template configuration for agent creation."""
        return self.configuration.get_template_configuration()
    
    def get_execution_params(self) -> dict[str, Any]:
        """Get execution parameters from configuration."""
        return self.configuration.get_execution_params()
    
    def get_toolset_names(self) -> list[str]:
        """Get toolset names from configuration."""
        return self.configuration.get_toolset_names()
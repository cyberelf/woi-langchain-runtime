"""Create agent command - Application layer."""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class CreateAgentCommand:
    """Command to create a new agent.
    
    Represents the intent to create a new agent in the system.
    """
    
    name: str
    template_id: str
    configuration: Dict[str, Any]
    template_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate command data."""
        if not self.name:
            raise ValueError("Agent name is required")
        if not self.template_id:
            raise ValueError("Template ID is required")
        if not isinstance(self.configuration, dict):
            raise ValueError("Configuration must be a dictionary")
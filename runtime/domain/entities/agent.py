"""Agent entity - Pure domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from ..value_objects.agent_id import AgentId


class AgentStatus(Enum):
    """Agent status enumeration."""
    
    CREATED = "created"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class Agent:
    """Agent entity - Core business logic for agents.
    
    This entity represents an agent configuration and its lifecycle.
    No framework dependencies - pure domain entity.
    """
    
    id: AgentId
    name: str
    template_id: str
    template_version: Optional[str]
    configuration: Dict[str, Any]
    status: AgentStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate agent data."""
        if not self.name:
            raise ValueError("Agent name cannot be empty")
        if not self.template_id:
            raise ValueError("Template ID cannot be empty")
        if not isinstance(self.configuration, dict):
            raise ValueError("Configuration must be a dictionary")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
    
    @classmethod
    def create(
        cls,
        name: str,
        template_id: str,
        configuration: Dict[str, Any],
        template_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Agent":
        """Create a new agent."""
        now = datetime.utcnow()
        return cls(
            id=AgentId.generate(),
            name=name,
            template_id=template_id,
            template_version=template_version,
            configuration=configuration.copy(),
            status=AgentStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=metadata.copy() if metadata else {}
        )
    
    def update_configuration(self, new_configuration: Dict[str, Any]) -> None:
        """Update agent configuration."""
        if not isinstance(new_configuration, dict):
            raise ValueError("Configuration must be a dictionary")
        
        self.configuration = new_configuration.copy()
        self.updated_at = datetime.utcnow()
    
    def update_status(self, new_status: AgentStatus) -> None:
        """Update agent status."""
        if not isinstance(new_status, AgentStatus):
            raise ValueError("Status must be an AgentStatus enum")
        
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    def activate(self) -> None:
        """Activate the agent."""
        self.update_status(AgentStatus.ACTIVE)
    
    def deactivate(self) -> None:
        """Deactivate the agent."""
        self.update_status(AgentStatus.INACTIVE)
    
    def mark_error(self) -> None:
        """Mark agent as having an error."""
        self.update_status(AgentStatus.ERROR)
    
    def is_active(self) -> bool:
        """Check if agent is active."""
        return self.status == AgentStatus.ACTIVE
    
    def is_configured_properly(self) -> bool:
        """Check if agent has valid configuration."""
        return bool(self.configuration and self.template_id)
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.configuration.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self.configuration[key] = value
        self.updated_at = datetime.utcnow()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the agent."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def __eq__(self, other) -> bool:
        """Equality based on ID."""
        if not isinstance(other, Agent):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)
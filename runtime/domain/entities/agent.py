"""Agent entity - Pure domain model."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional, Any
from enum import Enum

from ..value_objects.agent_id import AgentId
from ..value_objects.agent_configuration import AgentConfiguration


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
    configuration: AgentConfiguration
    status: AgentStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate agent data."""
        if not self.name:
            raise ValueError("Agent name cannot be empty")
        if not self.template_id:
            raise ValueError("Template ID cannot be empty")
        if not isinstance(self.configuration, AgentConfiguration):
            raise ValueError("Configuration must be an AgentConfiguration instance")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
    
    @classmethod
    def create(
        cls,
        name: str,
        template_id: str,
        configuration: AgentConfiguration,
        template_version: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ) -> "Agent":
        """Create a new agent."""
        now = datetime.now(UTC)
        return cls(
            id=AgentId.from_string(agent_id) if agent_id else AgentId.generate(),
            name=name,
            template_id=template_id,
            template_version=template_version,
            configuration=configuration,
            status=AgentStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=metadata.copy() if metadata else {}
        )
    
    def update_configuration(self, new_configuration: AgentConfiguration) -> None:
        """Update agent configuration."""
        if not isinstance(new_configuration, AgentConfiguration):
            raise ValueError("Configuration must be an AgentConfiguration instance")
        
        self.configuration = new_configuration
        self.updated_at = datetime.now(UTC)
    
    def update_status(self, new_status: AgentStatus) -> None:
        """Update agent status."""
        if not isinstance(new_status, AgentStatus):
            raise ValueError("Status must be an AgentStatus enum")
        
        self.status = new_status
        self.updated_at = datetime.now(UTC)
    
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
    
    def get_template_configuration(self) -> dict[str, Any]:
        """Get template configuration for execution."""
        return self.configuration.get_template_configuration()
    
    def get_execution_params(self) -> dict[str, Any]:
        """Get execution parameters from configuration."""
        return self.configuration.get_execution_params()
    
    def get_toolset_names(self) -> list[str]:
        """Get toolset names from configuration."""
        return self.configuration.get_toolset_names()
    
    def get_temperature(self) -> Optional[float]:
        """Get temperature from configuration."""
        return self.configuration.get_temperature()
    
    def get_max_tokens(self) -> Optional[int]:
        """Get max_tokens from configuration."""
        return self.configuration.get_max_tokens()
    
    def get_system_prompt(self) -> Optional[str]:
        """Get system prompt from configuration."""
        return self.configuration.system_prompt
    
    def get_llm_config_id(self) -> Optional[str]:
        """Get LLM config ID from configuration."""
        return self.configuration.llm_config_id
    
    def with_conversation_config(self, **config_values) -> "Agent":
        """Create a new agent with updated conversation config.
        
        Args:
            **config_values: Configuration values to update
            
        Returns:
            New Agent instance with updated configuration
        """
        new_config = self.configuration.with_conversation_config(**config_values)
        return Agent(
            id=self.id,
            name=self.name,
            template_id=self.template_id,
            template_version=self.template_version,
            configuration=new_config,
            status=self.status,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            metadata=self.metadata.copy()
        )
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the agent."""
        self.metadata[key] = value
        self.updated_at = datetime.now(UTC)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "template_id": self.template_id,
            "template_version": self.template_version,
            "configuration": self.configuration.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Agent":
        """Create from dictionary."""
        return cls(
            id=AgentId.from_string(data["id"]),
            name=data["name"],
            template_id=data["template_id"],
            template_version=data.get("template_version"),
            configuration=AgentConfiguration.from_dict(data["configuration"]),
            status=AgentStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {})
        )
    
    def __eq__(self, other) -> bool:
        """Equality based on ID."""
        if not isinstance(other, Agent):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)
    
    def __str__(self) -> str:
        """String representation."""
        return f"Agent(id={self.id}, name='{self.name}', template='{self.template_id}', status={self.status.value})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"Agent(id={self.id}, name='{self.name}', template_id='{self.template_id}', status={self.status})"
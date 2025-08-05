"""Agent ID value object - Pure domain model."""

from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass(frozen=True)
class AgentId:
    """Agent identifier value object.
    
    Immutable value object representing a unique agent identifier.
    No framework dependencies - pure domain concept.
    """
    
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Agent ID cannot be empty")
        if not isinstance(self.value, str):
            raise ValueError("Agent ID must be a string")
    
    @classmethod
    def generate(cls) -> "AgentId":
        """Generate a new unique agent ID."""
        return cls(str(uuid.uuid4()))
    
    @classmethod
    def from_string(cls, value: str) -> "AgentId":
        """Create AgentId from string value."""
        return cls(value)
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, AgentId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
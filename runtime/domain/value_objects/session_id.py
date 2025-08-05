"""Session ID value object - Pure domain model."""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class SessionId:
    """Session identifier value object.
    
    Immutable value object representing a unique chat session identifier.
    No framework dependencies - pure domain concept.
    """
    
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Session ID cannot be empty")
        if not isinstance(self.value, str):
            raise ValueError("Session ID must be a string")
    
    @classmethod
    def generate(cls) -> "SessionId":
        """Generate a new unique session ID."""
        return cls(str(uuid.uuid4()))
    
    @classmethod
    def from_string(cls, value: str) -> "SessionId":
        """Create SessionId from string value."""
        return cls(value)
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, SessionId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
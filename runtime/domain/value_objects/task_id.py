"""Task ID value object - domain identifier for Agent tasks.

A Task represents a long-lived stateful conversation between an agent and user(s). 
- Messages are atomic interactions
- Tasks are conversations containing multiple messages
- Contexts group related tasks

See also: ContextId for higher-level grouping."""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class TaskId:
    """Immutable identifier for long-lived agent tasks."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Task ID cannot be empty")
        if not isinstance(self.value, str):
            raise ValueError("Task ID must be a string")

    @classmethod
    def generate(cls) -> "TaskId":
        """Generate a new unique task ID."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> "TaskId":
        """Create a TaskId from a raw string."""
        return cls(value)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:  # type: ignore[override]
        if not isinstance(other, TaskId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

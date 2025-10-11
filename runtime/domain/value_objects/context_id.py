"""Identifier for higher-level execution contexts.

Groups related AgentTasks (e.g., all tasks within a multi-agent workflow).
Currently modeled as a simple value object; if context-specific business logic
emerges (lifecycle management, permissions, routing), consider promoting to
a full aggregate root."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextId:
    """Identifier for higher-level execution contexts.

    Keeps the domain explicit without forcing a dedicated aggregate today.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Context ID cannot be empty")
        if not isinstance(self.value, str):
            raise ValueError("Context ID must be a string")

    @classmethod
    def from_optional(cls, value: str | None) -> "ContextId | None":
        """Create a ContextId from an optional string."""
        if value is None:
            return None
        return cls(value)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:  # type: ignore[override]
        if not isinstance(other, ContextId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

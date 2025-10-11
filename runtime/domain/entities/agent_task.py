"""Agent task entity - Domain model for long-lived agent conversations."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..value_objects.task_id import TaskId
from ..value_objects.agent_id import AgentId
from ..value_objects.context_id import ContextId
from ..value_objects.chat_message import ChatMessage


@dataclass
class AgentTask:
    """Aggregate representing a stateful agent task (formerly chat session)."""

    id: TaskId
    agent_id: AgentId
    user_id: Optional[str]
    conversation_history: List[ChatMessage]
    created_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_history_length: int = 100
    context_id: Optional[ContextId] = None

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_history, list):
            raise ValueError("Conversation history must be a list")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
        if self.max_history_length <= 0:
            raise ValueError("Max history length must be positive")

    @classmethod
    def create(
        cls,
        agent_id: AgentId,
        user_id: Optional[str] = None,
        max_history_length: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
        context_id: Optional[ContextId] = None
    ) -> "AgentTask":
        """Create a new agent task aggregate."""
        now = datetime.utcnow()
        return cls(
            id=TaskId.generate(),
            agent_id=agent_id,
            user_id=user_id,
            conversation_history=[],
            created_at=now,
            last_activity=now,
            metadata=metadata.copy() if metadata else {},
            max_history_length=max_history_length,
            context_id=context_id
        )

    def add_message(self, message: ChatMessage) -> None:
        """Append a message to the conversation history and maintain limits."""
        if not isinstance(message, ChatMessage):
            raise ValueError("Message must be a ChatMessage")

        self.conversation_history.append(message)
        self.last_activity = datetime.utcnow()

        if len(self.conversation_history) > self.max_history_length:
            system_messages = [msg for msg in self.conversation_history if msg.is_system_message()]
            other_messages = [msg for msg in self.conversation_history if not msg.is_system_message()]

            messages_to_keep = self.max_history_length - len(system_messages)
            other_messages = other_messages[-messages_to_keep:] if messages_to_keep > 0 else []
            self.conversation_history = system_messages + other_messages

    def get_recent_messages(self, count: int) -> List[ChatMessage]:
        if count <= 0:
            return []
        return self.conversation_history[-count:]

    def get_user_messages(self) -> List[ChatMessage]:
        return [msg for msg in self.conversation_history if msg.is_user_message()]

    def get_assistant_messages(self) -> List[ChatMessage]:
        return [msg for msg in self.conversation_history if msg.is_assistant_message()]

    def get_message_count(self) -> int:
        return len(self.conversation_history)

    def is_expired(self, timeout_hours: int = 24) -> bool:
        if timeout_hours <= 0:
            return False
        timeout_delta = timedelta(hours=timeout_hours)
        return datetime.utcnow() - self.last_activity > timeout_delta

    def touch(self) -> None:
        self.last_activity = datetime.utcnow()

    def clear_history(self) -> None:
        self.conversation_history.clear()
        self.last_activity = datetime.utcnow()

    def set_max_history_length(self, length: int) -> None:
        if length <= 0:
            raise ValueError("Max history length must be positive")
        self.max_history_length = length

        if len(self.conversation_history) > length:
            system_messages = [msg for msg in self.conversation_history if msg.is_system_message()]
            other_messages = [msg for msg in self.conversation_history if not msg.is_system_message()]

            messages_to_keep = length - len(system_messages)
            other_messages = other_messages[-messages_to_keep:] if messages_to_keep > 0 else []
            self.conversation_history = system_messages + other_messages

    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
        self.touch()

    def set_context(self, context: ContextId | None) -> None:
        self.context_id = context
        self.touch()

    def __eq__(self, other) -> bool:  # type: ignore[override]
        if not isinstance(other, AgentTask):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

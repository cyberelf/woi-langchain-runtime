"""Domain events - Pure domain concepts."""

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Dict

from ..value_objects.agent_id import AgentId
from ..value_objects.task_id import TaskId


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event."""
    
    occurred_at: datetime
    event_id: str
    
    @classmethod
    def create(cls, **kwargs):
        """Create event with timestamp."""
        import uuid
        return cls(
            occurred_at=datetime.now(UTC),
            event_id=str(uuid.uuid4()),
            **kwargs
        )


@dataclass(frozen=True)
class AgentCreated(DomainEvent):
    """Event raised when an agent is created."""
    
    agent_id: AgentId
    agent_name: str
    template_id: str
    
    @classmethod
    def create(cls, agent_id: AgentId, agent_name: str, template_id: str):
        """Create AgentCreated event."""
        import uuid
        return cls(
            occurred_at=datetime.now(UTC),
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            agent_name=agent_name,
            template_id=template_id
        )


@dataclass(frozen=True)
class AgentStatusChanged(DomainEvent):
    """Event raised when an agent status changes."""
    
    agent_id: AgentId
    old_status: str
    new_status: str
    
    @classmethod
    def create(cls, agent_id: AgentId, old_status: str, new_status: str):
        """Create AgentStatusChanged event."""
        import uuid
        return cls(
            occurred_at=datetime.now(UTC),
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            old_status=old_status,
            new_status=new_status
        )


@dataclass(frozen=True)
class TaskStarted(DomainEvent):
    """Event raised when an agent task is started."""

    task_id: TaskId
    agent_id: AgentId
    user_id: str

    @classmethod
    def create(cls, task_id: TaskId, agent_id: AgentId, user_id: str):
        """Create TaskStarted event."""
        import uuid
        return cls(
            occurred_at=datetime.now(UTC),
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=agent_id,
            user_id=user_id
        )


@dataclass(frozen=True)
class TaskMessageAdded(DomainEvent):
    """Event raised when a message is added to a task."""

    task_id: TaskId
    message_role: str
    message_content: str

    @classmethod
    def create(cls, task_id: TaskId, message_role: str, message_content: str):
        """Create TaskMessageAdded event."""
        import uuid
        return cls(
            occurred_at=datetime.now(UTC),
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            message_role=message_role,
            message_content=message_content
        )


# Backward-compatible aliases
SessionStarted = TaskStarted
MessageAdded = TaskMessageAdded
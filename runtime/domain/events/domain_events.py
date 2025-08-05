"""Domain events - Pure domain concepts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from ..value_objects.agent_id import AgentId
from ..value_objects.session_id import SessionId


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
            occurred_at=datetime.utcnow(),
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
            occurred_at=datetime.utcnow(),
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
            occurred_at=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            old_status=old_status,
            new_status=new_status
        )


@dataclass(frozen=True)
class SessionStarted(DomainEvent):
    """Event raised when a chat session is started."""
    
    session_id: SessionId
    agent_id: AgentId
    user_id: str
    
    @classmethod
    def create(cls, session_id: SessionId, agent_id: AgentId, user_id: str):
        """Create SessionStarted event."""
        import uuid
        return cls(
            occurred_at=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id
        )


@dataclass(frozen=True)
class MessageAdded(DomainEvent):
    """Event raised when a message is added to a session."""
    
    session_id: SessionId
    message_role: str
    message_content: str
    
    @classmethod
    def create(cls, session_id: SessionId, message_role: str, message_content: str):
        """Create MessageAdded event."""
        import uuid
        return cls(
            occurred_at=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            message_role=message_role,
            message_content=message_content
        )
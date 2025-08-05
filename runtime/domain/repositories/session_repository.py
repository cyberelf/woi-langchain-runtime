"""Session repository interface - Pure domain contract."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.chat_session import ChatSession
from ..value_objects.session_id import SessionId
from ..value_objects.agent_id import AgentId


class SessionRepositoryInterface(ABC):
    """Repository interface for ChatSession entities.
    
    This interface defines the contract for session persistence without
    specifying implementation details. Pure domain interface.
    """
    
    @abstractmethod
    async def save(self, session: ChatSession) -> None:
        """Save a chat session."""
        pass
    
    @abstractmethod
    async def get_by_id(self, session_id: SessionId) -> Optional[ChatSession]:
        """Get a session by ID."""
        pass
    
    @abstractmethod
    async def get_by_agent_and_user(self, agent_id: AgentId, user_id: str) -> Optional[ChatSession]:
        """Get a session by agent ID and user ID."""
        pass
    
    @abstractmethod
    async def list_by_agent(self, agent_id: AgentId) -> List[ChatSession]:
        """List sessions by agent ID."""
        pass
    
    @abstractmethod
    async def list_by_user(self, user_id: str) -> List[ChatSession]:
        """List sessions by user ID."""
        pass
    
    @abstractmethod
    async def list_active(self, timeout_hours: int = 24) -> List[ChatSession]:
        """List active (non-expired) sessions."""
        pass
    
    @abstractmethod
    async def list_expired(self, timeout_hours: int = 24) -> List[ChatSession]:
        """List expired sessions."""
        pass
    
    @abstractmethod
    async def exists(self, session_id: SessionId) -> bool:
        """Check if session exists."""
        pass
    
    @abstractmethod
    async def delete(self, session_id: SessionId) -> bool:
        """Delete a session."""
        pass
    
    @abstractmethod
    async def delete_expired(self, timeout_hours: int = 24) -> int:
        """Delete expired sessions and return count."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Count total sessions."""
        pass
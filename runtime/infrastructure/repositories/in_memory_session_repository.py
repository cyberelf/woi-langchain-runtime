"""In-memory session repository implementation - Infrastructure layer."""

from typing import Dict, List, Optional

from ...domain.entities.chat_session import ChatSession
from ...domain.repositories.session_repository import SessionRepositoryInterface
from ...domain.value_objects.session_id import SessionId
from ...domain.value_objects.agent_id import AgentId


class InMemorySessionRepository(SessionRepositoryInterface):
    """In-memory implementation of session repository.
    
    Infrastructure layer implementation that provides concrete
    persistence for session entities using in-memory storage.
    """
    
    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}
    
    async def save(self, session: ChatSession) -> None:
        """Save a chat session."""
        self._sessions[session.id.value] = session
    
    async def get_by_id(self, session_id: SessionId) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id.value)
    
    async def get_by_agent_and_user(self, agent_id: AgentId, user_id: str) -> Optional[ChatSession]:
        """Get a session by agent ID and user ID."""
        for session in self._sessions.values():
            if session.agent_id == agent_id and session.user_id == user_id:
                return session
        return None
    
    async def list_by_agent(self, agent_id: AgentId) -> List[ChatSession]:
        """List sessions by agent ID."""
        return [
            session for session in self._sessions.values()
            if session.agent_id == agent_id
        ]
    
    async def list_by_user(self, user_id: str) -> List[ChatSession]:
        """List sessions by user ID."""
        return [
            session for session in self._sessions.values()
            if session.user_id == user_id
        ]
    
    async def list_active(self, timeout_hours: int = 24) -> List[ChatSession]:
        """List active (non-expired) sessions."""
        return [
            session for session in self._sessions.values()
            if not session.is_expired(timeout_hours)
        ]
    
    async def list_expired(self, timeout_hours: int = 24) -> List[ChatSession]:
        """List expired sessions."""
        return [
            session for session in self._sessions.values()
            if session.is_expired(timeout_hours)
        ]
    
    async def exists(self, session_id: SessionId) -> bool:
        """Check if session exists."""
        return session_id.value in self._sessions
    
    async def delete(self, session_id: SessionId) -> bool:
        """Delete a session."""
        if session_id.value in self._sessions:
            del self._sessions[session_id.value]
            return True
        return False
    
    async def delete_expired(self, timeout_hours: int = 24) -> int:
        """Delete expired sessions and return count."""
        expired_sessions = await self.list_expired(timeout_hours)
        count = 0
        
        for session in expired_sessions:
            if await self.delete(session.id):
                count += 1
        
        return count
    
    async def count(self) -> int:
        """Count total sessions."""
        return len(self._sessions)
    
    def clear(self) -> None:
        """Clear all sessions (for testing)."""
        self._sessions.clear()
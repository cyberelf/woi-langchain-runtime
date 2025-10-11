"""In-memory Unit of Work implementation - Infrastructure layer."""

from typing import Optional

from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ..repositories.in_memory_agent_repository import InMemoryAgentRepository
from ..repositories.in_memory_task_repository import InMemoryTaskRepository


class InMemoryUnitOfWork(UnitOfWorkInterface):
    """In-memory implementation of Unit of Work.
    
    Infrastructure layer implementation that manages transactions
    across multiple repositories using in-memory storage.
    """
    
    def __init__(self):
        self.agents = InMemoryAgentRepository()
        self.tasks = InMemoryTaskRepository()
        self._committed = False
        self._rolled_back = False
    
    async def commit(self) -> None:
        """Commit the current transaction.
        
        For in-memory implementation, this is a no-op since
        changes are already applied to the repositories.
        """
        if self._rolled_back:
            raise RuntimeError("Cannot commit after rollback")
        
        self._committed = True
    
    async def rollback(self) -> None:
        """Rollback the current transaction.
        
        For in-memory implementation, we would need to track
        changes to undo them. For simplicity, we just mark
        as rolled back and prevent further operations.
        """
        if self._committed:
            raise RuntimeError("Cannot rollback after commit")
        
        self._rolled_back = True
    
    async def __aenter__(self):
        """Enter async context manager."""
        self._committed = False
        self._rolled_back = False
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if exc_type is not None:
            # Exception occurred, rollback
            await self.rollback()
        elif not self._committed and not self._rolled_back:
            # No exception and not yet committed, auto-commit
            await self.commit()
    
    def is_committed(self) -> bool:
        """Check if transaction is committed."""
        return self._committed
    
    def is_rolled_back(self) -> bool:
        """Check if transaction is rolled back."""
        return self._rolled_back


class TransactionalInMemoryUnitOfWork(UnitOfWorkInterface):
    """More sophisticated in-memory UoW with transaction tracking.
    
    This implementation tracks changes and can actually rollback
    by maintaining snapshots of repository state.
    """
    
    def __init__(self):
        # Shared repositories for all UoW instances
        if not hasattr(TransactionalInMemoryUnitOfWork, '_shared_agent_repo'):
            TransactionalInMemoryUnitOfWork._shared_agent_repo = InMemoryAgentRepository()
            TransactionalInMemoryUnitOfWork._shared_task_repo = InMemoryTaskRepository()
        
        self.agents = TransactionalInMemoryUnitOfWork._shared_agent_repo
        self.tasks = TransactionalInMemoryUnitOfWork._shared_task_repo
        
        # Transaction state
        self._agent_snapshot: Optional[dict] = None
        self._task_snapshot: Optional[dict] = None
        self._committed = False
        self._rolled_back = False
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._rolled_back:
            raise RuntimeError("Cannot commit after rollback")
        
        # Clear snapshots since we're committing
        self._agent_snapshot = None
        self._task_snapshot = None
        self._committed = True
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._committed:
            raise RuntimeError("Cannot rollback after commit")
        
        # Restore from snapshots
        if self._agent_snapshot is not None:
            self.agents._agents = self._agent_snapshot.copy()  # type: ignore[attr-defined]

        if self._task_snapshot is not None:
            self.tasks._tasks = self._task_snapshot.copy()  # type: ignore[attr-defined]
        
        self._rolled_back = True
    
    async def __aenter__(self):
        """Enter async context manager."""
        # Take snapshots for potential rollback
        self._agent_snapshot = self.agents._agents.copy()  # type: ignore[attr-defined]
        self._task_snapshot = self.tasks._tasks.copy()  # type: ignore[attr-defined]
        
        self._committed = False
        self._rolled_back = False
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if exc_type is not None:
            # Exception occurred, rollback
            await self.rollback()
        elif not self._committed and not self._rolled_back:
            # No exception and not yet committed, auto-commit
            await self.commit()
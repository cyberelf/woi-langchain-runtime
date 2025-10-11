"""Unit of Work interface - Pure domain contract."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..repositories.agent_repository import AgentRepositoryInterface
    from ..repositories.task_repository import TaskRepositoryInterface


class UnitOfWorkInterface(ABC):
    """Unit of Work interface for transaction management.
    
    This interface defines the contract for managing transactions across
    multiple repositories. Pure domain interface.
    """
    
    # Repository properties (type hints for implementations)
    if TYPE_CHECKING:
        agents: "AgentRepositoryInterface"
        tasks: "TaskRepositoryInterface"
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        pass
    
    @abstractmethod
    async def __aenter__(self):
        """Enter async context manager."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        pass
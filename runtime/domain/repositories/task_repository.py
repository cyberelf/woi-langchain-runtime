"""Task repository interface - Pure domain contract."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.agent_task import AgentTask
from ..value_objects.task_id import TaskId
from ..value_objects.agent_id import AgentId
from ..value_objects.context_id import ContextId


class TaskRepositoryInterface(ABC):
    """Repository interface for AgentTask aggregates."""

    @abstractmethod
    async def save(self, task: AgentTask) -> None:
        pass

    @abstractmethod
    async def get_by_id(self, task_id: TaskId) -> Optional[AgentTask]:
        pass

    @abstractmethod
    async def get_by_agent_and_user(
        self,
        agent_id: AgentId,
        user_id: str,
        context_id: ContextId | None = None
    ) -> Optional[AgentTask]:
        pass

    @abstractmethod
    async def list_by_agent(self, agent_id: AgentId) -> List[AgentTask]:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> List[AgentTask]:
        pass

    @abstractmethod
    async def list_active(self, timeout_hours: int = 24) -> List[AgentTask]:
        pass

    @abstractmethod
    async def list_expired(self, timeout_hours: int = 24) -> List[AgentTask]:
        pass

    @abstractmethod
    async def exists(self, task_id: TaskId) -> bool:
        pass

    @abstractmethod
    async def delete(self, task_id: TaskId) -> bool:
        pass

    @abstractmethod
    async def delete_expired(self, timeout_hours: int = 24) -> int:
        pass

    @abstractmethod
    async def count(self) -> int:
        pass

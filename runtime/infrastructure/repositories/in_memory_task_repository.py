"""In-memory task repository implementation - Infrastructure layer."""

from typing import Dict, List, Optional

from ...domain.entities.agent_task import AgentTask
from ...domain.repositories.task_repository import TaskRepositoryInterface
from ...domain.value_objects.task_id import TaskId
from ...domain.value_objects.agent_id import AgentId
from ...domain.value_objects.context_id import ContextId


class InMemoryTaskRepository(TaskRepositoryInterface):
    """Simple in-memory storage for agent tasks (formerly sessions)."""

    def __init__(self) -> None:
        self._tasks: Dict[str, AgentTask] = {}

    async def save(self, task: AgentTask) -> None:
        self._tasks[task.id.value] = task

    async def get_by_id(self, task_id: TaskId) -> Optional[AgentTask]:
        return self._tasks.get(task_id.value)

    async def get_by_agent_and_user(
        self,
        agent_id: AgentId,
        user_id: str,
        context_id: ContextId | None = None
    ) -> Optional[AgentTask]:
        """Find a task by agent and user, optionally filtering by context.
    
        Args:
            context_id: If None, returns first matching task regardless of context.
                    If provided, only returns tasks with that exact context_id.
        """
        for task in self._tasks.values():
            if task.agent_id == agent_id and task.user_id == user_id:
                if context_id is None or task.context_id == context_id:
                    return task
        return None

    async def list_by_agent(self, agent_id: AgentId) -> List[AgentTask]:
        return [task for task in self._tasks.values() if task.agent_id == agent_id]

    async def list_by_user(self, user_id: str) -> List[AgentTask]:
        return [task for task in self._tasks.values() if task.user_id == user_id]

    async def list_active(self, timeout_hours: int = 24) -> List[AgentTask]:
        return [task for task in self._tasks.values() if not task.is_expired(timeout_hours)]

    async def list_expired(self, timeout_hours: int = 24) -> List[AgentTask]:
        return [task for task in self._tasks.values() if task.is_expired(timeout_hours)]

    async def exists(self, task_id: TaskId) -> bool:
        return task_id.value in self._tasks

    async def delete(self, task_id: TaskId) -> bool:
        if task_id.value in self._tasks:
            del self._tasks[task_id.value]
            return True
        return False

    async def delete_expired(self, timeout_hours: int = 24) -> int:
        expired = await self.list_expired(timeout_hours)
        deleted = 0
        for task in expired:
            if await self.delete(task.id):
                deleted += 1
        return deleted

    async def count(self) -> int:
        return len(self._tasks)

    def clear(self) -> None:
        self._tasks.clear()

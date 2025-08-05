"""Dependency injection for web layer - Infrastructure layer."""

from typing import Generator

from ...application.services.create_agent_service import CreateAgentService
from ...application.services.execute_agent_service import ExecuteAgentService
from ...application.services.query_agent_service import QueryAgentService
from ..unit_of_work.in_memory_uow import TransactionalInMemoryUnitOfWork


# Global UoW instance (in a real application, this would be managed by DI container)
_uow = TransactionalInMemoryUnitOfWork()


def get_unit_of_work() -> Generator[TransactionalInMemoryUnitOfWork, None, None]:
    """Get Unit of Work dependency."""
    yield _uow


def get_create_agent_service() -> CreateAgentService:
    """Get create agent service dependency."""
    return CreateAgentService(_uow)


def get_execute_agent_service() -> ExecuteAgentService:
    """Get execute agent service dependency."""
    # TODO: Inject actual agent runtime
    return ExecuteAgentService(_uow, agent_runtime=None)


def get_query_agent_service() -> QueryAgentService:
    """Get query agent service dependency."""
    return QueryAgentService(_uow)
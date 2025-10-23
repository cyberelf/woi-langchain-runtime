"""Dependency injection for the new task management architecture."""

import logging
from functools import lru_cache
from typing import Any, Optional

from runtime.domain.services.template_validation_service import TemplateValidationInterface

from ...settings import settings
from ...core.message_queue import MessageQueueInterface
from ..message_queues import create_message_queue
from ...core.agent_orchestrator import AgentOrchestrator
from ...core.executors import FrameworkExecutorInterface
from ..frameworks.langgraph.executor import LangGraphFrameworkExecutor
from ...application.services.execute_agent_service import ExecuteAgentService
from ...application.services.create_agent_service import CreateAgentService
from ...application.services.query_agent_service import QueryAgentService
from ...application.services.update_agent_service import UpdateAgentService
from ...application.services.delete_agent_service import DeleteAgentService
from ...application.services.update_agent_status_service import UpdateAgentStatusService
from ...application.services.compose_agent_service import ComposeAgentService
from ..unit_of_work.in_memory_uow import TransactionalInMemoryUnitOfWork
from ..frameworks.langgraph.llm.service import LangGraphLLMService

logger = logging.getLogger(__name__)

# Global instances for the new architecture
_message_queue: Optional[MessageQueueInterface] = None
_framework_executor: Optional[FrameworkExecutorInterface] = None
_orchestrator: Optional[AgentOrchestrator] = None
_execute_service: Optional[ExecuteAgentService] = None
_agent_template_validator: Optional[TemplateValidationInterface] = None


@lru_cache()
def get_message_queue() -> MessageQueueInterface:
    """Get message queue instance."""
    global _message_queue
    
    if _message_queue is None:
        logger.info(f"Initializing message queue: {settings.message_queue_type}")
        
        if settings.message_queue_type == "redis":
            _message_queue = create_message_queue("redis", redis_url=settings.redis_url)
        elif settings.message_queue_type == "rabbitmq":
            _message_queue = create_message_queue("rabbitmq", amqp_url=settings.rabbitmq_url)
        else:
            _message_queue = create_message_queue("memory")
        
        logger.info(f"Message queue initialized: {type(_message_queue).__name__}")
    
    return _message_queue


@lru_cache()
def get_framework_executor() -> FrameworkExecutorInterface:
    """Get framework executor instance."""
    global _framework_executor
    
    if _framework_executor is None:
        logger.info(f"Initializing framework executor: {settings.default_framework}")
        
        if settings.default_framework == "langgraph":
            _framework_executor = LangGraphFrameworkExecutor()
        else:
            raise ValueError(f"Unsupported framework: {settings.default_framework}")
        
        logger.info(f"Framework executor initialized: {_framework_executor.name}")
    
    return _framework_executor


@lru_cache()
def get_unit_of_work() -> TransactionalInMemoryUnitOfWork:
    """Get unit of work instance."""
    return TransactionalInMemoryUnitOfWork()


@lru_cache()
def get_agent_template_validator() -> TemplateValidationInterface:
    """Get agent template validator instance."""
    global _agent_template_validator
    
    if _agent_template_validator is None:
        if settings.default_framework == "langgraph":
            _agent_template_validator = LangGraphFrameworkExecutor()
        else:
            raise ValueError(f"Unsupported framework: {settings.default_framework}")
    
    return _agent_template_validator


async def get_orchestrator() -> AgentOrchestrator:
    """Get agent orchestrator instance (A2A-aligned)."""
    global _orchestrator
    
    if _orchestrator is None:
        logger.info("Initializing agent orchestrator")
        
        message_queue = get_message_queue()
        uow = get_unit_of_work()
        framework_executor = get_framework_executor()
        
        _orchestrator = AgentOrchestrator(
            message_queue=message_queue,
            uow=uow,
            framework_executor=framework_executor,
            max_workers=settings.task_manager_workers,
            cleanup_interval_seconds=settings.task_cleanup_interval,
            instance_timeout_seconds=settings.instance_timeout
        )
        
        # Initialize orchestrator
        await _orchestrator.initialize()
        
        logger.info(f"Agent orchestrator initialized with {settings.task_manager_workers} workers")
    
    return _orchestrator


async def get_execute_agent_service() -> ExecuteAgentService:
    """Get execute agent service (A2A-aligned)."""
    global _execute_service
    
    if _execute_service is None:
        orchestrator = await get_orchestrator()
        _execute_service = ExecuteAgentService(orchestrator)
        logger.info("Execute agent service initialized with A2A terminology")
    
    return _execute_service


def get_create_agent_service() -> CreateAgentService:
    """Get create agent service dependency."""
    uow = get_unit_of_work()
    # Use the framework executor directly as the template validator
    # since it now implements TemplateValidationInterface
    template_validator = get_agent_template_validator()
    return CreateAgentService(uow, template_validator)


def get_query_agent_service() -> QueryAgentService:
    """Get query agent service dependency."""
    uow = get_unit_of_work()
    return QueryAgentService(uow)


def get_update_agent_service() -> UpdateAgentService:
    """Get update agent service dependency."""
    uow = get_unit_of_work()
    return UpdateAgentService(uow)


def get_delete_agent_service() -> DeleteAgentService:
    """Get delete agent service dependency."""
    uow = get_unit_of_work()
    return DeleteAgentService(uow)


def get_update_agent_status_service() -> UpdateAgentStatusService:
    """Get update agent status service dependency."""
    uow = get_unit_of_work()
    return UpdateAgentStatusService(uow)


def get_compose_agent_service() -> ComposeAgentService:
    """Get compose agent service dependency."""
    # Get framework executor which has LLM configuration
    framework_executor = get_framework_executor()
    
    # Create LLM service with framework's LLM config
    # The executor has the config already loaded
    from ..frameworks.langgraph.executor import LangGraphFrameworkExecutor
    if isinstance(framework_executor, LangGraphFrameworkExecutor):
        llm_service = framework_executor._llm_service
        if llm_service is None:
            llm_service = LangGraphLLMService()
    else:
        # Fallback: create default LLM service
        llm_service = LangGraphLLMService()
    
    return ComposeAgentService(llm_service, framework_executor)  # type: ignore


async def startup_dependencies():
    """Initialize all dependencies at startup."""
    logger.info("Starting up dependencies for new architecture")
    
    try:
        # Initialize message queue
        message_queue = get_message_queue()
        await message_queue.initialize()
        
        # Initialize framework executor
        framework_executor = get_framework_executor()
        await framework_executor.initialize()
        
        # Initialize orchestrator
        orchestrator = await get_orchestrator()
        # Orchestrator is initialized in get_orchestrator()
        
        logger.info("All dependencies initialized successfully")
        
        return {
            "message_queue": message_queue,
            "framework_executor": framework_executor,
            "orchestrator": orchestrator
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize dependencies: {e}")
        raise


async def shutdown_dependencies():
    """Shutdown all dependencies."""
    logger.info("Shutting down dependencies")
    
    global _orchestrator, _framework_executor, _message_queue, _execute_service
    
    try:
        # Shutdown orchestrator first
        if _orchestrator:
            await _orchestrator.shutdown()
            _orchestrator = None
        
        # Shutdown framework executor
        if _framework_executor:
            await _framework_executor.shutdown()
            _framework_executor = None
        
        # Shutdown message queue
        if _message_queue:
            await _message_queue.shutdown()
            _message_queue = None
        
        # Clear service instance
        _execute_service = None
        
        logger.info("All dependencies shutdown successfully")
        
    except Exception as e:
        logger.error(f"Error during dependency shutdown: {e}")


def get_architecture_info() -> dict[str, Any]:
    """Get information about the current architecture."""
    return {
        "architecture_version": "v2",
        "task_management": "enabled" if settings.task_manager_enabled else "disabled",
        "message_queue_type": settings.message_queue_type,
        "framework_executor": settings.default_framework,
        "max_workers": settings.task_manager_workers,
        "instance_timeout": settings.instance_timeout,
        "cleanup_interval": settings.task_cleanup_interval,
        "features": [
            "async_task_execution",
            "message_queue_orchestration", 
            "session_based_agents",
            "automatic_cleanup",
            "pure_framework_execution",
            "horizontal_scalability"
        ]
    }
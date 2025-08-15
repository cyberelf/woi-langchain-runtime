"""Execute Agent Service V2 - Using Task Manager and Message Queue Architecture."""

import logging
import uuid
from typing import Dict, Any, Optional, AsyncGenerator

from ...domain.value_objects.chat_message import ChatMessage
from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ...core.agent_task_manager import (
    AgentTaskManager, 
    AgentTaskRequest, 
    AgentTaskResult, 
    TaskStatus
)
from ...core.message_queue import MessagePriority
from ..commands.execute_agent_command import ExecuteAgentCommand

logger = logging.getLogger(__name__)


class ExecuteAgentServiceV2:
    """Execute agent application service using async task management.
    
    This service orchestrates agent execution by:
    1. Submitting tasks to the task manager
    2. Managing async execution via message queue
    3. Providing results and streaming capabilities
    4. Delegating all instance management to AgentTaskManager
    """
    
    def __init__(self, task_manager: AgentTaskManager):
        self.task_manager = task_manager
    
    async def execute(self, command: ExecuteAgentCommand) -> AgentTaskResult:
        """Execute an agent asynchronously via task manager.
        
        This method:
        1. Creates a task request from the command
        2. Submits to task manager for async execution
        3. Waits for and returns the result
        4. All instance management is handled by task manager
        """
        logger.info(f"Executing agent: {command.agent_id}")
        
        # Create task request
        task_request = AgentTaskRequest.create_execute_task(
            agent_id=command.agent_id,
            messages=command.messages,
            session_id=command.session_id,
            user_id=command.user_id,
            stream=command.stream,
            temperature=command.temperature,
            max_tokens=command.max_tokens,
            metadata=command.metadata,
            priority=MessagePriority.NORMAL,
            correlation_id=str(uuid.uuid4())
        )
        
        # Submit task for async execution
        task_id = await self.task_manager.submit_task(task_request)
        logger.debug(f"Submitted task {task_id} for agent {command.agent_id}")
        
        # Wait for result (with timeout)
        timeout_seconds = getattr(command, 'timeout_seconds', 300)  # 5 minutes default
        result = await self.task_manager.get_task_result(task_id, timeout_seconds)
        
        if not result:
            logger.error(f"Task {task_id} timed out after {timeout_seconds} seconds")
            # Create timeout result
            result = AgentTaskResult(
                task_id=task_id,
                agent_id=command.agent_id,
                status=TaskStatus.TIMEOUT,
                error=f"Task timed out after {timeout_seconds} seconds",
                processing_time_ms=timeout_seconds * 1000
            )
        
        logger.info(f"Agent execution completed: {command.agent_id}, status: {result.status.value}")
        return result
    
    async def execute_streaming(self, command: ExecuteAgentCommand) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute an agent with streaming response via task manager."""
        logger.info(f"Streaming execution for agent: {command.agent_id}")
        
        # Create streaming task request
        task_request = AgentTaskRequest.create_execute_task(
            agent_id=command.agent_id,
            messages=command.messages,
            session_id=command.session_id,
            user_id=command.user_id,
            stream=True,  # Force streaming
            temperature=command.temperature,
            max_tokens=command.max_tokens,
            metadata=command.metadata,
            priority=MessagePriority.HIGH,  # Higher priority for streaming
            correlation_id=str(uuid.uuid4())
        )
        
        # Submit streaming task
        task_id = await self.task_manager.submit_task(task_request)
        logger.debug(f"Submitted streaming task {task_id} for agent {command.agent_id}")
        
        # Stream results
        try:
            async for chunk_data in self.task_manager.stream_task_results(task_id):
                # Convert internal chunk format to OpenAI-compatible format
                openai_chunk = {
                    "id": chunk_data.get('id', str(uuid.uuid4())),
                    "object": "chat.completion.chunk",
                    "created": chunk_data.get('created', 0),
                    "model": command.agent_id,
                    "choices": chunk_data.get('choices', [{
                        "index": 0,
                        "delta": {"content": chunk_data.get('content', '')},
                        "finish_reason": chunk_data.get('finish_reason')
                    }])
                }
                
                # Add usage info if available
                if 'usage' in chunk_data:
                    openai_chunk['usage'] = chunk_data['usage']
                
                yield openai_chunk
                
        except Exception as e:
            logger.error(f"Streaming execution failed: {e}")
            # Yield error chunk
            yield {
                "id": str(uuid.uuid4()),
                "object": "chat.completion.chunk",
                "created": 0,
                "model": command.agent_id,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "error"
                }],
                "error": str(e)
            }
    
    async def get_agent_instances(self) -> list[Dict[str, Any]]:
        """Get list of managed agent instances."""
        return await self.task_manager.list_agent_instances()
    
    async def destroy_session_agent(self, agent_id: str, session_id: str) -> bool:
        """Destroy a session agent."""
        return await self.task_manager.destroy_agent_instance(agent_id, session_id)
    
    async def cleanup_inactive_sessions(self) -> None:
        """Clean up inactive session agents."""
        # This is now handled automatically by task manager's cleanup worker
        logger.info("Session cleanup is handled automatically by task manager")
    
    async def get_task_manager_health(self) -> Dict[str, Any]:
        """Get task manager health status."""
        return {
            "task_manager_running": self.task_manager._running,
            "worker_count": len(self.task_manager._task_workers),
            "active_instances": len(self.task_manager._agent_instances),
            "running_tasks": len(self.task_manager._running_tasks),
            "message_queue_type": type(self.task_manager.message_queue).__name__
        }


# Adapter class for backward compatibility
class AgentExecutionResult:
    """Backward compatibility adapter for AgentTaskResult."""
    
    def __init__(self, task_result: AgentTaskResult):
        self._task_result = task_result
        
        # Map task result to old format
        self.response_id = task_result.task_id
        self.agent_id = task_result.agent_id
        self.message = task_result.message or ""
        self.finish_reason = task_result.finish_reason or "stop"
        self.prompt_tokens = task_result.prompt_tokens
        self.completion_tokens = task_result.completion_tokens
        self.total_tokens = task_result.total_tokens
        self.processing_time_ms = task_result.processing_time_ms
        self.metadata = task_result.metadata
        self.created_at = int(task_result.created_at.timestamp())
        
        # Handle status mapping
        if task_result.status == TaskStatus.COMPLETED:
            self.success = True
            self.error = None
        else:
            self.success = False
            self.error = task_result.error or f"Task failed with status: {task_result.status.value}"


class ExecuteAgentServiceAdapter:
    """Adapter to maintain backward compatibility with existing API.
    
    This adapter wraps ExecuteAgentServiceV2 to provide the same interface
    as the original ExecuteAgentService while using the new task management system.
    """
    
    def __init__(self, task_manager: AgentTaskManager):
        self._service = ExecuteAgentServiceV2(task_manager)
    
    async def execute(self, command: ExecuteAgentCommand) -> AgentExecutionResult:
        """Execute agent and return result in old format."""
        task_result = await self._service.execute(command)
        return AgentExecutionResult(task_result)
    
    async def _execute_streaming_real(
        self, 
        agent_instance, 
        messages: list[ChatMessage], 
        command: ExecuteAgentCommand, 
        start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming execution using new task manager (backward compatibility)."""
        async for chunk in self._service.execute_streaming(command):
            yield chunk
    
    async def _execute_streaming_mock(
        self, 
        agent, 
        command: ExecuteAgentCommand, 
        start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Mock streaming (replaced by real streaming via task manager)."""
        async for chunk in self._service.execute_streaming(command):
            yield chunk
    
    # Delegate other methods
    async def get_agent_instances(self) -> list[Dict[str, Any]]:
        return await self._service.get_agent_instances()
    
    async def destroy_session_agent(self, agent_id: str, session_id: str) -> bool:
        return await self._service.destroy_session_agent(agent_id, session_id)
    
    async def cleanup_inactive_sessions(self) -> None:
        await self._service.cleanup_inactive_sessions()
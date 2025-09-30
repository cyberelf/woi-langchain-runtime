"""Execute Agent Service - Clean application service using Task Manager."""

import logging
import uuid
from typing import Any
from collections.abc import AsyncGenerator

from ...core.executors import ExecutionResult, StreamingChunk
from ...core.agent_orchestrator import (
    AgentOrchestrator, 
    AgentMessageRequest
)
from ...core.message_queue import MessagePriority
from ..commands.execute_agent_command import ExecuteAgentCommand

logger = logging.getLogger(__name__)


class ExecuteAgentService:
    """Execute agent application service using async orchestration.
    
    This service orchestrates agent execution by:
    1. Submitting messages to the orchestrator (A2A Messages)
    2. Managing async execution via message queue
    3. Providing results and streaming capabilities
    4. Delegating all instance management to AgentOrchestrator
    5. Generating server-side task_ids for stateful conversations (A2A Tasks)
    """
    
    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator
    
    async def execute(self, command: ExecuteAgentCommand) -> ExecutionResult:
        """Execute an agent and return core ExecutionResult.
        
        This method:
        1. Creates a task request from the command
        2. Submits to task manager for async execution
        3. Waits for result and converts to core ExecutionResult
        4. All instance management is handled by task manager
        """
        logger.info(f"🚀 Executing agent: {command.agent_id}")
        
        # Generate server-side task_id if this is a stateful conversation
        # The command may already have a task_id from a previous message in the same conversation
        task_id = command.session_id or str(uuid.uuid4())  # For now, map session_id to task_id
        logger.debug(f"🆔 Task ID assigned: {task_id} (session: {command.session_id})")
        
        # Create message request (A2A Message)
        correlation_id = str(uuid.uuid4())
        message_request = AgentMessageRequest.create_execute_message(
            agent_id=command.agent_id,
            messages=command.messages,
            task_id=task_id,  # Stateful conversation ID
            context_id=command.metadata.get('context_id') if command.metadata else None,
            user_id=command.user_id,
            stream=False,  # Non-streaming execution
            temperature=command.temperature or 0.7,
            max_tokens=command.max_tokens,
            metadata=command.metadata,
            priority=MessagePriority.NORMAL,
            correlation_id=correlation_id
        )
        
        logger.debug(f"📝 Created message request - correlation: {correlation_id}, "
                    f"priority: {MessagePriority.NORMAL.value}, streaming: False")
        
        # Submit message for async execution
        message_id = await self.orchestrator.submit_message(message_request)
        logger.debug(f"Submitted message {message_id} for agent {command.agent_id} in task {task_id}")
        
        # Wait for result (with timeout)
        timeout_seconds = getattr(command, 'timeout_seconds', 300)  # 5 minutes default
        logger.debug(f"⏳ Waiting for result with {timeout_seconds}s timeout...")
        
        execution_result = await self.orchestrator.get_message_result(message_id, timeout_seconds)
        
        if not execution_result:
            logger.error(f"Message {message_id} timed out after {timeout_seconds} seconds")
            return ExecutionResult(
                success=False,
                error=f"Message timed out after {timeout_seconds} seconds",
                processing_time_ms=timeout_seconds * 1000,
                message_id=message_id,
                task_id=task_id,
                agent_id=command.agent_id
            )
        
        logger.debug(f"📥 Received result for message {message_id} "
                    f"processing time: {execution_result.processing_time_ms}ms)")
        
        # ExecutionResult is now returned directly from message manager
        # Ensure it has the proper identifiers
        if not execution_result.task_id:
            execution_result.task_id = task_id
        if not execution_result.agent_id:
            execution_result.agent_id = command.agent_id
        if not execution_result.message_id:
            execution_result.message_id = message_id
        
        if execution_result.success:
            logger.info(f"✅ Agent execution completed: {command.agent_id}, "
                       f"tokens: {execution_result.total_tokens}, "
                       f"time: {execution_result.processing_time_ms}ms")
            logger.debug(f"📊 Result details - {execution_result}")
        else:
            logger.error(f"❌ Agent execution failed: {command.agent_id}, "
                        f"error: {execution_result.error}",
                        f"details: {execution_result}")
        
        return execution_result
    
    async def execute_streaming(self, command: ExecuteAgentCommand) -> AsyncGenerator[StreamingChunk, None]:
        """Execute an agent with streaming response, returning core StreamingChunk objects."""
        logger.info(f"Streaming execution for agent: {command.agent_id}")
        
        # Generate server-side task_id for stateful conversation  
        task_id = command.session_id or str(uuid.uuid4())
        logger.debug(f"🆔 Streaming task ID assigned: {task_id} (session: {command.session_id})")
        
        # Create streaming message request (A2A Message)
        correlation_id = str(uuid.uuid4())
        message_request = AgentMessageRequest.create_execute_message(
            agent_id=command.agent_id,
            messages=command.messages,
            task_id=task_id,  # Stateful conversation ID
            context_id=command.metadata.get('context_id') if command.metadata else None,
            user_id=command.user_id,
            stream=True,  # Force streaming
            temperature=command.temperature or 0.7,
            max_tokens=command.max_tokens,
            metadata=command.metadata,
            priority=MessagePriority.HIGH,  # Higher priority for streaming
            correlation_id=correlation_id
        )
        
        logger.debug(f"📝 Created streaming message request - correlation: {correlation_id}, "
                    f"priority: {MessagePriority.HIGH.value}, streaming: True")
        
        # Submit streaming message
        message_id = await self.orchestrator.submit_message(message_request)
        logger.debug(
            f"Submitted streaming message {message_id} for agent {command.agent_id} in task {task_id}"
        )
        
        # Stream results - return core StreamingChunk objects only
        logger.debug(f"📺 Starting stream consumption for message {message_id}")
        chunk_count = 0
        total_content_length = 0

        try:
            async for chunk_data in self.orchestrator.stream_message_results(message_id):
                chunk_count += 1
                content = chunk_data.get('content', '')
                finish_reason = chunk_data.get('finish_reason')
                total_content_length += len(content)

                logger.debug(f"📦 Chunk #{chunk_count}: {len(content)} chars, "
                           f"finish_reason: {finish_reason}")

                # Convert orchestrator chunk to core StreamingChunk
                chunk = StreamingChunk(
                    content=content,
                    finish_reason=finish_reason,
                    message_id=message_id,  # A2A Message ID
                    task_id=task_id,        # A2A Task ID
                    metadata={
                        'agent_id': command.agent_id,
                        'context_id': command.metadata.get('context_id') if command.metadata else None,
                        'chunk_number': chunk_count,
                        **(chunk_data.get('metadata', {}))
                    }
                )
                yield chunk

                # Log completion when stream finishes
                if finish_reason:
                    logger.info(f"✅ Streaming completed for {command.agent_id}: "
                              f"{chunk_count} chunks, {total_content_length} chars, ")
                    logger.debug(f"🏁 Final chunk finish_reason: {finish_reason}")
                    break

        except Exception as e:
            logger.error(f"❌ Streaming execution failed for {command.agent_id} after "
                        f"{chunk_count} chunks: {e}")
            # Yield error chunk as core type
            yield StreamingChunk(
                content="",
                finish_reason="error",
                message_id=message_id,  # A2A Message ID
                task_id=task_id,        # A2A Task ID
                metadata={
                    'agent_id': command.agent_id,
                    'error': str(e),
                    'chunks_received': chunk_count
                }
            )
    
    async def get_agent_instances(self) -> list[dict[str, Any]]:
        """Get list of managed agent instances."""
        return await self.orchestrator.list_agent_instances()
    
    async def destroy_task_agent(self, agent_id: str, task_id: str) -> bool:
        """Destroy a task agent (A2A Task context)."""
        return await self.orchestrator.destroy_agent_instance(agent_id, task_id)
    
    async def cleanup_inactive_tasks(self) -> None:
        """Clean up inactive task agents."""
        # This is now handled automatically by orchestrator's cleanup worker
        logger.info("Task cleanup is handled automatically by orchestrator")
    
    async def get_orchestrator_health(self) -> dict[str, Any]:
        """Get orchestrator health status."""
        return {
            "orchestrator_running": self.orchestrator._running,
            "worker_count": len(self.orchestrator._message_workers),
            "active_instances": len(self.orchestrator._agent_instances),
            "running_messages": len(self.orchestrator._running_messages),
            "message_queue_type": type(self.orchestrator.message_queue).__name__
        }

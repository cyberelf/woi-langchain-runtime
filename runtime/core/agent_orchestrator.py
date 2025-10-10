"""Agent Orchestrator - A2A-aligned async execution with message queue orchestration.

This system orchestrates A2A Messages (individual executions) within A2A Tasks (stateful conversations).
Terminology aligned with A2A Protocol specification:
- Message: Single atomic execution/interaction 
- Task: Stateful conversation containing multiple messages
- Context: Broader grouping mechanism for related tasks
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Optional
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

from .executors import AgentExecutorInterface, FrameworkExecutorInterface, ExecutionResult, StreamingChunk

from .message_queue import MessageQueueInterface, QueueMessage as MessageQueueItem, MessagePriority
from .queue_message_models import (
    StreamingChunkQueueMessage,
    ExecutionResultQueueMessage,
    create_streaming_chunk_message,
    create_execution_result_message,
)
from ..domain.entities.agent import Agent
from ..domain.value_objects.agent_id import AgentId
from ..domain.value_objects.chat_message import ChatMessage
from ..domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ..infrastructure.adapters.api_adapters import api_adapter_registry


logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Agent message types (A2A Message types)."""
    EXECUTE = "execute"
    STREAM_EXECUTE = "stream_execute"
    CLEANUP = "cleanup"
    HEALTH_CHECK = "health_check"


# MessageStatus is imported from message_queue module


@dataclass
class AgentMessageRequest:
    """Agent message execution request (A2A Message)."""
    message_id: str       # Single atomic execution ID (A2A Message)
    message_type: MessageType
    agent_id: str
    task_id: Optional[str] = None    # Stateful conversation ID (A2A Task) - server-generated
    context_id: Optional[str] = None # Broader grouping context
    user_id: Optional[str] = None
    messages: list[ChatMessage] = field(default_factory=list)
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    @classmethod
    def create_execute_message(
        cls,
        agent_id: str,
        messages: list[ChatMessage],
        task_id: Optional[str] = None,    # A2A Task ID for stateful conversation
        context_id: Optional[str] = None, # Broader grouping context
        user_id: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> "AgentMessageRequest":
        """Create an agent execution message (A2A Message)."""
        return cls(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.EXECUTE if not stream else MessageType.STREAM_EXECUTE,
            agent_id=agent_id,
            task_id=task_id,
            context_id=context_id,
            user_id=user_id,
            messages=messages,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata or {},
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for queue serialization."""
        return {
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'agent_id': self.agent_id,
            'task_id': self.task_id,
            'context_id': self.context_id,
            'user_id': self.user_id,
            'messages': [msg.to_dict() for msg in self.messages],
            'stream': self.stream,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'metadata': self.metadata,
            'timeout_seconds': self.timeout_seconds,
            'priority': self.priority.value,
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMessageRequest":
        """Create from dictionary."""
        messages = [ChatMessage.from_dict(msg_data) for msg_data in data.get('messages', [])]
        return cls(
            message_id=data['message_id'],
            message_type=MessageType(data['message_type']),
            agent_id=data['agent_id'],
            task_id=data.get('task_id'),
            context_id=data.get('context_id'),
            user_id=data.get('user_id'),
            messages=messages,
            stream=data.get('stream', False),
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens'),
            metadata=data.get('metadata', {}),
            timeout_seconds=data.get('timeout_seconds', 300),
            priority=MessagePriority(data.get('priority', MessagePriority.NORMAL.value)),
            correlation_id=data.get('correlation_id'),
            reply_to=data.get('reply_to')
        )




@dataclass
class AgentInstance:
    """Agent instance managed by the message manager (A2A Task context)."""
    agent_id: str
    task_id: Optional[str]  # A2A Task ID (stateful conversation)
    agent: Agent
    framework_agent: AgentExecutorInterface
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0
    is_active: bool = True
    
    @property
    def instance_key(self) -> str:
        """Get unique instance key."""
        if self.task_id:
            return f"{self.agent_id}#{self.task_id}"
        return self.agent_id
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(UTC)
        self.message_count += 1


class AgentOrchestrator:
    """Orchestrates agent instances and async message execution via message queue.
    
    A2A-aligned terminology:
    - Messages: Individual atomic executions (what we previously called 'tasks')
    - Tasks: Stateful conversations containing multiple messages (what we previously called 'sessions')
    - Context: Broader grouping mechanism for related tasks
    
    This orchestrator handles the complete lifecycle of agent execution including:
    - Message queue coordination
    - Agent instance management (A2A Task contexts)
    - Framework executor integration
    - Result streaming and collection
    """
    
    def __init__(
        self,
        message_queue: MessageQueueInterface,
        uow: UnitOfWorkInterface,
        framework_executor: FrameworkExecutorInterface,
        max_workers: int = 10,
        cleanup_interval_seconds: int = 3600,  # 1 hour
        instance_timeout_seconds: int = 7200   # 2 hours
    ):
        self.message_queue = message_queue
        self.uow = uow
        self.framework_executor = framework_executor
        self.max_workers = max_workers
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.instance_timeout_seconds = instance_timeout_seconds
        
        # Agent instance management
        self._agent_instances: dict[str, AgentInstance] = {}
        self._message_results: dict[str, ExecutionResult] = {}
        self._instance_lock = asyncio.Lock()
        
        # Message execution
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_messages: dict[str, asyncio.Task] = {}
        self._message_workers: list[asyncio.Task] = []
        
        # Framework integration
        self._framework = None

        
        # Control flags
        self._running = False
        self._cleanup_task = None
        
        # Queue names (A2A aligned)
        self.MESSAGE_QUEUE = "agent.messages"  # For individual message executions
        self.RESULT_QUEUE = "agent.results"
        self.STREAM_QUEUE_PREFIX = "agent.stream."
    
    async def initialize(self) -> None:
        """Initialize the message manager."""
        logger.info("Initializing Agent Message Manager")
        
        # Initialize framework executor
        await self.framework_executor.initialize()
        
        # Initialize message queue
        await self.message_queue.initialize()
        
        # Create queues
        await self.message_queue.create_queue(self.MESSAGE_QUEUE)
        await self.message_queue.create_queue(self.RESULT_QUEUE)
        
        # Start message workers
        self._running = True
        self._message_workers = [
            asyncio.create_task(self._message_worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        logger.info(f"Started {self.max_workers} message workers")
    
    async def shutdown(self) -> None:
        """Shutdown the agent orchestrator."""
        logger.info("Shutting down Agent Orchestrator")
        
        # Stop workers
        self._running = False
        
        # Cancel running messages
        for task in self._running_messages.values():
            task.cancel()
        
        # Wait for workers to finish
        if self._message_workers:
            await asyncio.gather(*self._message_workers, return_exceptions=True)
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Cleanup agent instances
        async with self._instance_lock:
            for instance in self._agent_instances.values():
                # Agent executor is stateless, no cleanup needed
                logger.debug(f"Destroying agent instance {instance.instance_key}")
            self._agent_instances.clear()
        
        # Shutdown message queue
        await self.message_queue.shutdown()
        
        # Shutdown framework executor
        await self.framework_executor.shutdown()
        
        # Shutdown thread pool executor
        self._executor.shutdown(wait=True)
        
        logger.info("Agent Orchestrator shutdown complete")
    
    async def submit_message(self, message_request: AgentMessageRequest) -> str:
        """Submit an agent message for async execution."""
        logger.info(f"Submitting message {message_request.message_id} for agent {message_request.agent_id}")
        
        # Send message to queue
        queue_message_id = await self.message_queue.send_message(
            queue_name=self.MESSAGE_QUEUE,
            payload=message_request.to_dict(),
            priority=message_request.priority,
            correlation_id=message_request.correlation_id,
            reply_to=message_request.reply_to or self.RESULT_QUEUE,
            metadata={
                'message_type': message_request.message_type.value,
                'agent_id': message_request.agent_id,
                'task_id': message_request.task_id,
                'context_id': message_request.context_id,
                'submitted_at': datetime.now(UTC).isoformat()
            }
        )
        
        logger.debug(f"Message {message_request.message_id} queued as queue message {queue_message_id}")
        return message_request.message_id
    
    async def get_message_result(
        self, message_id: str, timeout_seconds: Optional[int] = None
    ) -> Optional[ExecutionResult]:
        """Get message execution result."""
        # Check local cache first
        if message_id in self._message_results:
            return self._message_results[message_id]
        
        # Wait for result from queue
        start_time = time.time()
        while (
            timeout_seconds is None or (time.time() - start_time) < timeout_seconds
        ):
            message = await self.message_queue.receive_message(
                queue_name=self.RESULT_QUEUE,
                timeout_seconds=1
            )
            
            if message and message.payload.get('message_id') == message_id:
                await self.message_queue.acknowledge_message(message)

                # Parse the queue message as our internal format
                queue_message = ExecutionResultQueueMessage.model_validate(message.payload)

                # Convert internal queue message to domain model
                result = api_adapter_registry.domain_adapter.execution_result_to_domain(queue_message)
                self._message_results[message_id] = result
                return result
            
            await asyncio.sleep(0.1)
        
        return None
    
    async def stream_message_results(self, message_id: str) -> AsyncGenerator[StreamingChunk, None]:
        """Stream message execution results for streaming messages."""
        stream_queue = f"{self.STREAM_QUEUE_PREFIX}{message_id}"

        logger.debug(f"Stream message from queue: {stream_queue}")

        try:
            while True:
                message = await self.message_queue.receive_message(
                    queue_name=stream_queue,
                    timeout_seconds=30  # 30 second timeout
                )
                logger.debug(f"Stream message results: {message}")
                
                if not message:
                    break
                
                # Parse the queue message as our internal format
                queue_message = StreamingChunkQueueMessage.model_validate(message.payload)
                await self.message_queue.acknowledge_message(message)

                # Check for stream end marker
                if queue_message.metadata.get('stream_end', False):
                    break

                # Convert internal queue message to domain model
                domain_chunk = api_adapter_registry.domain_adapter.streaming_chunk_to_domain(queue_message)
                yield domain_chunk
        finally:
            # Cleanup stream queue
            await self.message_queue.delete_queue(stream_queue)
    
    async def agent_exists(self, agent_id: str) -> bool:
        """Check if an agent exists in the repository."""
        try:
            async with self.uow:
                agent_id_vo = AgentId.from_string(agent_id)
                agent = await self.uow.agents.get_by_id(agent_id_vo)
                return agent is not None
        except Exception:
            return False

    async def get_or_create_agent_instance(
        self,
        agent_id: str,
        task_id: Optional[str] = None
    ) -> AgentInstance:
        """Get or create an agent instance."""
        instance_key = f"{agent_id}#{task_id}" if task_id else agent_id
        logger.debug(f"🔍 Getting agent instance: {instance_key}")
        
        async with self._instance_lock:
            # Check existing instance
            if instance_key in self._agent_instances:
                instance = self._agent_instances[instance_key]
                instance.update_activity()
                logger.debug(f"♻️  Reusing existing agent instance: {instance_key} "
                           f"(last activity: {instance.last_activity}, messages: {instance.message_count})")
                return instance
            
            logger.debug(f"🏗️  Creating new agent instance for {instance_key}")
            
            # Load agent from repository
            async with self.uow:
                agent_id_vo = AgentId.from_string(agent_id)
                agent = await self.uow.agents.get_by_id(agent_id_vo)
                if not agent:
                    logger.error(f"❌ Agent {agent_id} not found in repository")
                    raise ValueError(f"Agent {agent_id} not found")
                
                logger.debug(f"📋 Loaded agent: {agent.name} (template: {agent.template_id})")
            
            # Get the stateless agent executor from framework
            framework_agent = self.framework_executor.agent_executor
            
            # Create managed instance
            instance = AgentInstance(
                agent_id=agent_id,
                task_id=task_id,
                agent=agent,
                framework_agent=framework_agent
            )
            
            self._agent_instances[instance_key] = instance
            logger.info(f"✅ Created agent instance: {instance_key} "
                       f"(total instances: {len(self._agent_instances)})")
            logger.debug(f"🏷️  Instance details - agent: {agent.name}, "
                        f"template: {agent.template_id}, created: {instance.created_at}")
            return instance
    
    async def destroy_agent_instance(self, agent_id: str, task_id: Optional[str] = None) -> bool:
        """Destroy an agent instance."""
        instance_key = f"{agent_id}#{task_id}" if task_id else agent_id
        
        async with self._instance_lock:
            if instance_key in self._agent_instances:
                # Agent executor is stateless, no cleanup needed
                logger.debug(f"Removing agent instance {instance_key}")
                
                # Remove from managed instances
                del self._agent_instances[instance_key]
                logger.info(f"Destroyed agent instance: {instance_key}")
                return True
        
        return False
    
    async def list_agent_instances(self) -> list[dict[str, Any]]:
        """List all managed agent instances."""
        async with self._instance_lock:
            return [
                {
                    'instance_key': instance.instance_key,
                    'agent_id': instance.agent_id,
                    'task_id': instance.task_id,
                    'created_at': instance.created_at.isoformat(),
                    'last_activity': instance.last_activity.isoformat(),
                    'message_count': instance.message_count,
                    'is_active': instance.is_active
                }
                for instance in self._agent_instances.values()
            ]
    
    async def _message_worker(self, worker_id: str) -> None:
        """Message worker that processes messages from the message queue."""
        logger.info(f"Message worker {worker_id} started")
        
        while self._running:
            try:
                logger.debug(f"Worker {worker_id} waiting for messages...")
                # Receive message from queue
                message = await self.message_queue.receive_message(
                    queue_name=self.MESSAGE_QUEUE,
                    timeout_seconds=5
                )
                
                if not message:
                    continue
                
                # Parse message request
                message_request = AgentMessageRequest.from_dict(message.payload)
                logger.debug(f"Worker {worker_id} processing message {message_request.message_id}")
                
                try:
                    # Execute message
                    if message_request.message_type == MessageType.EXECUTE:
                        result = await self._execute_agent_message(message_request)
                    elif message_request.message_type == MessageType.STREAM_EXECUTE:
                        result = await self._execute_streaming_message(message_request)
                    else:
                        result = ExecutionResult(
                            success=False,
                            error=f"Unsupported message type: {message_request.message_type}",
                            message_id=message_request.message_id,
                            task_id=message_request.task_id,
                            agent_id=message_request.agent_id,
                            context_id=message_request.context_id
                        )
                    
                    # Send result
                    await self._send_message_result(message, result)
                    
                    # Acknowledge message
                    await self.message_queue.acknowledge_message(message)
                    
                except Exception as e:
                    logger.error(f"Message execution failed: {e}")
                    
                    # Send error result
                    error_result = ExecutionResult(
                        success=False,
                        error=str(e),
                        message_id=message_request.message_id,
                        task_id=message_request.task_id,
                        agent_id=message_request.agent_id,
                        context_id=message_request.context_id
                    )
                    await self._send_message_result(message, error_result)
                    
                    # Reject message
                    await self.message_queue.reject_message(message, requeue=False, reason=str(e))
            
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Message worker {worker_id} stopped")
    
    async def _execute_agent_message(self, message_request: AgentMessageRequest) -> ExecutionResult:
        """Execute a regular agent message."""
        logger.debug(f"🎯 Executing agent message: {message_request.message_id} "
                    f"(agent: {message_request.agent_id}, task: {message_request.task_id})")
        start_time = time.time()
        
        # Get agent instance
        instance = await self.get_or_create_agent_instance(
            message_request.agent_id,
            message_request.task_id
        )
        
        try:
            # Get execution parameters from agent configuration
            agent_exec_params = instance.agent.get_execution_params()
            logger.debug(f"🔧 Agent execution params: {agent_exec_params}")
            
            # Merge agent defaults with request overrides (request takes precedence)
            final_temperature = message_request.temperature
            final_max_tokens = message_request.max_tokens
            if final_max_tokens is None:
                final_max_tokens = agent_exec_params.get("max_tokens")
            
            logger.debug(f"⚙️  Final execution parameters - temperature: {final_temperature}, "
                        f"max_tokens: {final_max_tokens}, messages: {len(message_request.messages)}")
            
            # Execute using framework agent
            exec_start = time.time()
            response = await instance.framework_agent.execute(
                template_id=instance.agent.template_id,
                template_version=instance.agent.template_version or "v1.0.0",
                configuration=instance.agent.get_template_configuration(),
                messages=message_request.messages,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                metadata={
                    # Agent static context
                    "agent_id": instance.agent_id,
                    "agent_name": instance.agent.name,
                    "template_id": instance.agent.template_id,
                    "template_version": instance.agent.template_version or "v1.0.0",
                    # Dynamic execution context (A2A aligned)
                    "task_id": message_request.task_id,
                    "message_id": message_request.message_id,
                    "context_id": message_request.context_id,
                    "user_id": message_request.user_id,
                    **(message_request.metadata or {})
                }
            )
            exec_time = (time.time() - exec_start) * 1000
            logger.debug(f"⚡ Framework execution completed in {exec_time:.2f}ms")
            
            # Convert response (ExecutionResult already has the correct structure)
            processing_time = int((time.time() - start_time) * 1000)
            
            # Update response with A2A identifiers
            response.processing_time_ms = processing_time
            response.message_id = message_request.message_id
            response.task_id = message_request.task_id
            response.agent_id = message_request.agent_id
            response.context_id = message_request.context_id
            
            # Add execution metadata
            response.metadata.update({
                "user_id": message_request.user_id,
                "instance_key": instance.instance_key,
                "message_type": message_request.message_type.value
            })
            
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time,
                message_id=message_request.message_id,
                task_id=message_request.task_id,
                agent_id=message_request.agent_id,
                context_id=message_request.context_id
            )
    
    async def _execute_streaming_message(self, message_request: AgentMessageRequest) -> ExecutionResult:
        """Execute a streaming agent message."""
        logger.debug(f"🌊 Executing streaming message: {message_request.message_id} "
                    f"(agent: {message_request.agent_id}, task: {message_request.task_id})")
        start_time = time.time()
        stream_queue = f"{self.STREAM_QUEUE_PREFIX}{message_request.message_id}"
        
        # Create stream queue
        logger.debug(f"📺 Creating stream queue: {stream_queue}")
        await self.message_queue.create_queue(stream_queue)
        
        # Get agent instance
        instance = await self.get_or_create_agent_instance(
            message_request.agent_id,
            message_request.task_id
        )
        
        try:
            # Get execution parameters from agent configuration
            agent_exec_params = instance.agent.get_execution_params()
            
            # Merge agent defaults with request overrides (request takes precedence)
            final_temperature = message_request.temperature
            final_max_tokens = message_request.max_tokens
            if final_max_tokens is None:
                final_max_tokens = agent_exec_params.get("max_tokens")
            
            # Stream execution
            logger.debug(f"🔄 Starting stream execution with {len(message_request.messages)} messages")
            chunk_count = 0
            total_content_length = 0
            
            async for chunk in instance.framework_agent.stream_execute(
                template_id=instance.agent.template_id,
                template_version=instance.agent.template_version or "v1.0.0",
                configuration=instance.agent.get_template_configuration(),
                messages=message_request.messages,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                metadata={
                    # Agent static context
                    "agent_id": instance.agent_id,
                    "agent_name": instance.agent.name,
                    "template_id": instance.agent.template_id,
                    "template_version": instance.agent.template_version or "v1.0.0",
                    # Dynamic execution context (A2A aligned)
                    "task_id": message_request.task_id,
                    "message_id": message_request.message_id,
                    "context_id": message_request.context_id,
                    "user_id": message_request.user_id,
                    **(message_request.metadata or {})
                }
            ):
                chunk_count += 1
                content = getattr(chunk, 'content', '')
                finish_reason = getattr(chunk, 'finish_reason', None)
                original_chunk_index = getattr(chunk, 'chunk_index', chunk_count - 1)
                total_content_length += len(content)

                logger.debug(f"📦 Stream chunk #{chunk_count}: {len(content)} chars, "
                           f"finish: {finish_reason}")

                # Send chunk to stream queue using internal queue message model
                queue_message = create_streaming_chunk_message(
                    message_id=message_request.message_id,
                    task_id=message_request.task_id or "",
                    agent_id=message_request.agent_id,
                    content=content,
                    chunk_index=original_chunk_index,
                    finish_reason=finish_reason,
                    context_id=message_request.context_id,
                    metadata={
                        "chunk_id": getattr(chunk, 'id', str(uuid.uuid4())),
                        "user_id": message_request.user_id,
                        "template_id": instance.agent.template_id,
                        "template_version": instance.agent.template_version or "v1.0.0",
                        **(message_request.metadata or {})
                    }
                )

                await self.message_queue.send_message(
                    queue_name=stream_queue,
                    payload=queue_message.model_dump(),
                    priority=MessagePriority.HIGH
                )
                
            logger.debug(f"🏁 Stream execution completed: {chunk_count} chunks, "
                        f"{total_content_length} total chars")
            
            # Send stream end marker using internal queue message model
            end_message = create_streaming_chunk_message(
                message_id=message_request.message_id,
                task_id=message_request.task_id or "",
                agent_id=message_request.agent_id,
                content="",
                chunk_index=chunk_count + 1,
                finish_reason="stop",
                context_id=message_request.context_id,
                metadata={
                    "stream_end": True,
                    "total_chunks": chunk_count,
                    "user_id": message_request.user_id,
                    **(message_request.metadata or {})
                }
            )

            await self.message_queue.send_message(
                queue_name=stream_queue,
                payload=end_message.model_dump(),
                priority=MessagePriority.HIGH
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return ExecutionResult(
                success=True,
                message=f"Streaming completed with {chunk_count} chunks",
                finish_reason="stop",
                processing_time_ms=processing_time,
                message_id=message_request.message_id,
                task_id=message_request.task_id,
                agent_id=message_request.agent_id,
                context_id=message_request.context_id,
                metadata={
                    "stream_queue": stream_queue,
                    "chunk_count": chunk_count,
                    "user_id": message_request.user_id,
                    "message_type": message_request.message_type.value
                }
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            
            # Send error to stream
            await self.message_queue.send_message(
                queue_name=stream_queue,
                payload={"error": str(e), "stream_end": True},
                priority=MessagePriority.HIGH
            )
            
            return ExecutionResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time,
                message_id=message_request.message_id,
                task_id=message_request.task_id,
                agent_id=message_request.agent_id,
                context_id=message_request.context_id
            )
    
    async def _send_message_result(self, original_message: MessageQueueItem, result: ExecutionResult) -> None:
        """Send message result to reply queue."""
        reply_to = original_message.reply_to or self.RESULT_QUEUE

        # Convert ExecutionResult domain model to queue payload for sending
        queue_payload = create_execution_result_message(
            message_id=result.message_id or "",
            task_id=result.task_id or "",
            agent_id=result.agent_id or "",
            success=result.success,
            content=result.message or "",
            error=result.error,
            processing_time_ms=result.processing_time_ms,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            context_id=result.context_id,
            metadata=result.metadata
        )

        await self.message_queue.send_message(
            queue_name=reply_to,
            payload=queue_payload.model_dump(),
            correlation_id=original_message.correlation_id,
            metadata={
                'original_message_id': original_message.payload.get('message_id'),
                'original_task_id': original_message.payload.get('task_id'),
                'completed_at': datetime.now(UTC).isoformat()
            }
        )
    
    async def _cleanup_worker(self) -> None:
        """Background worker for cleaning up inactive agent instances."""
        logger.info("Cleanup worker started")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                
                if not self._running:
                    break
                
                await self._cleanup_inactive_instances()
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
        
        logger.info("Cleanup worker stopped")
    
    async def _cleanup_inactive_instances(self) -> None:
        """Clean up inactive agent instances."""
        now = datetime.now(UTC)
        timeout_threshold = self.instance_timeout_seconds
        
        instances_to_remove = []
        
        logger.debug(f"🧹 Starting cleanup check - timeout: {timeout_threshold}s, "
                    f"total instances: {len(self._agent_instances)}")
        
        async with self._instance_lock:
            for instance_key, instance in self._agent_instances.items():
                inactive_seconds = (now - instance.last_activity).total_seconds()
                
                logger.debug(f"📊 Instance {instance_key}: inactive for {inactive_seconds:.1f}s")
                
                if inactive_seconds > timeout_threshold:
                    instances_to_remove.append(instance_key)
                    logger.debug(f"🗑️  Marking {instance_key} for removal "
                               f"(inactive: {inactive_seconds:.1f}s > {timeout_threshold}s)")
        
        # Remove inactive instances
        for instance_key in instances_to_remove:
            try:
                agent_id = instance_key.split('#')[0]
                task_id = instance_key.split('#')[1] if '#' in instance_key else None
                await self.destroy_agent_instance(agent_id, task_id)
                logger.info(f"🧹 Cleaned up inactive instance: {instance_key}")
            except Exception as e:
                logger.error(f"❌ Failed to cleanup instance {instance_key}: {e}")
        
        if instances_to_remove:
            logger.info(f"✅ Cleaned up {len(instances_to_remove)} inactive agent instances "
                       f"(remaining: {len(self._agent_instances)})")
        else:
            logger.debug(f"✨ No instances need cleanup (active: {len(self._agent_instances)})")
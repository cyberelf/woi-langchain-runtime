"""Agent Task Management System - Async execution with message queue orchestration."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
from concurrent.futures import ThreadPoolExecutor

from runtime.infrastructure.frameworks.executor_base import AgentExecutorInterface

from .message_queue import MessageQueueInterface, QueueMessage, MessagePriority, MessageStatus
from ..domain.entities.agent import Agent
from ..domain.value_objects.agent_id import AgentId
from ..domain.value_objects.chat_message import ChatMessage, MessageRole
from ..domain.unit_of_work.unit_of_work import UnitOfWorkInterface


logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Agent task types."""
    EXECUTE = "execute"
    STREAM_EXECUTE = "stream_execute"
    CLEANUP = "cleanup"
    HEALTH_CHECK = "health_check"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class AgentTaskRequest:
    """Agent task execution request."""
    task_id: str
    task_type: TaskType
    agent_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    messages: List[ChatMessage] = field(default_factory=list)
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    @classmethod
    def create_execute_task(
        cls,
        agent_id: str,
        messages: List[ChatMessage],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> "AgentTaskRequest":
        """Create an agent execution task."""
        return cls(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.EXECUTE if not stream else TaskType.STREAM_EXECUTE,
            agent_id=agent_id,
            session_id=session_id,
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for queue serialization."""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type.value,
            'agent_id': self.agent_id,
            'session_id': self.session_id,
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
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTaskRequest":
        """Create from dictionary."""
        messages = [ChatMessage.from_dict(msg_data) for msg_data in data.get('messages', [])]
        return cls(
            task_id=data['task_id'],
            task_type=TaskType(data['task_type']),
            agent_id=data['agent_id'],
            session_id=data.get('session_id'),
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
class AgentTaskResult:
    """Agent task execution result."""
    task_id: str
    agent_id: str
    status: TaskStatus
    message: Optional[str] = None
    finish_reason: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    processing_time_ms: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'status': self.status.value,
            'message': self.message,
            'finish_reason': self.finish_reason,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'processing_time_ms': self.processing_time_ms,
            'error': self.error,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTaskResult":
        """Create AgentTaskResult from dictionary."""
        # Convert status string back to enum
        status = TaskStatus(data['status']) if isinstance(data['status'], str) else data['status']
        
        # Convert datetime string back to datetime
        created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        
        # Remove computed fields
        clean_data = data.copy()
        clean_data.pop('total_tokens', None)
        
        return cls(
            task_id=clean_data['task_id'],
            agent_id=clean_data['agent_id'],
            status=status,
            message=clean_data.get('message'),
            finish_reason=clean_data.get('finish_reason'),
            prompt_tokens=clean_data.get('prompt_tokens', 0),
            completion_tokens=clean_data.get('completion_tokens', 0),
            processing_time_ms=clean_data.get('processing_time_ms', 0),
            error=clean_data.get('error'),
            metadata=clean_data.get('metadata', {}),
            created_at=created_at
        )


@dataclass
class AgentInstance:
    """Agent instance managed by the task manager."""
    agent_id: str
    session_id: Optional[str]
    agent: Agent
    framework_agent: AgentExecutorInterface
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0
    is_active: bool = True
    
    @property
    def instance_key(self) -> str:
        """Get unique instance key."""
        if self.session_id:
            return f"{self.agent_id}#{self.session_id}"
        return self.agent_id
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(UTC)
        self.message_count += 1


class AgentTaskManager:
    """Manages agent instances and async task execution via message queue."""
    
    def __init__(
        self,
        message_queue: MessageQueueInterface,
        uow: UnitOfWorkInterface,
        max_workers: int = 10,
        cleanup_interval_seconds: int = 3600,  # 1 hour
        instance_timeout_seconds: int = 7200   # 2 hours
    ):
        self.message_queue = message_queue
        self.uow = uow
        self.max_workers = max_workers
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.instance_timeout_seconds = instance_timeout_seconds
        
        # Agent instance management
        self._agent_instances: Dict[str, AgentInstance] = {}
        self._task_results: Dict[str, AgentTaskResult] = {}
        self._instance_lock = asyncio.Lock()
        
        # Task execution
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_workers: List[asyncio.Task] = []
        
        # Framework integration
        self._framework = None

        
        # Control flags
        self._running = False
        self._cleanup_task = None
        
        # Queue names
        self.TASK_QUEUE = "agent.tasks"
        self.RESULT_QUEUE = "agent.results"
        self.STREAM_QUEUE_PREFIX = "agent.stream."
    
    async def initialize(self, framework) -> None:
        """Initialize the task manager."""
        logger.info("Initializing Agent Task Manager")
        
        # Store framework reference
        self._framework = framework
        await self._framework.initialize()
        # Framework executor is used directly, no factory needed
        
        # Initialize message queue
        await self.message_queue.initialize()
        
        # Create queues
        await self.message_queue.create_queue(self.TASK_QUEUE)
        await self.message_queue.create_queue(self.RESULT_QUEUE)
        
        # Start task workers
        self._running = True
        self._task_workers = [
            asyncio.create_task(self._task_worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        logger.info(f"Started {self.max_workers} task workers")
    
    async def shutdown(self) -> None:
        """Shutdown the task manager."""
        logger.info("Shutting down Agent Task Manager")
        
        # Stop workers
        self._running = False
        
        # Cancel running tasks
        for task in self._running_tasks.values():
            task.cancel()
        
        # Wait for workers to finish
        if self._task_workers:
            await asyncio.gather(*self._task_workers, return_exceptions=True)
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Cleanup agent instances
        async with self._instance_lock:
            for instance in self._agent_instances.values():
                try:
                    await instance.framework_agent.cleanup()
                except Exception as e:
                    logger.warning(f"Error destroying agent instance {instance.instance_key}: {e}")
            self._agent_instances.clear()
        
        # Shutdown message queue
        await self.message_queue.shutdown()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        logger.info("Agent Task Manager shutdown complete")
    
    async def submit_task(self, task_request: AgentTaskRequest) -> str:
        """Submit an agent task for async execution."""
        logger.info(f"Submitting task {task_request.task_id} for agent {task_request.agent_id}")
        
        # Send task to queue
        message_id = await self.message_queue.send_message(
            queue_name=self.TASK_QUEUE,
            payload=task_request.to_dict(),
            priority=task_request.priority,
            correlation_id=task_request.correlation_id,
            reply_to=task_request.reply_to or self.RESULT_QUEUE,
            metadata={
                'task_type': task_request.task_type.value,
                'agent_id': task_request.agent_id,
                'session_id': task_request.session_id,
                'submitted_at': datetime.now(UTC).isoformat()
            }
        )
        
        logger.debug(f"Task {task_request.task_id} queued as message {message_id}")
        return task_request.task_id
    
    async def get_task_result(self, task_id: str, timeout_seconds: Optional[int] = None) -> Optional[AgentTaskResult]:
        """Get task execution result."""
        # Check local cache first
        if task_id in self._task_results:
            return self._task_results[task_id]
        
        # Wait for result from queue
        start_time = time.time()
        while timeout_seconds is None or (time.time() - start_time) < timeout_seconds:
            message = await self.message_queue.receive_message(
                queue_name=self.RESULT_QUEUE,
                timeout_seconds=1
            )
            
            if message and message.payload.get('task_id') == task_id:
                await self.message_queue.acknowledge_message(message)
                result = AgentTaskResult.from_dict(message.payload)
                self._task_results[task_id] = result
                return result
            
            await asyncio.sleep(0.1)
        
        return None
    
    async def stream_task_results(self, task_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream task execution results for streaming tasks."""
        stream_queue = f"{self.STREAM_QUEUE_PREFIX}{task_id}"
        
        # Create stream queue
        await self.message_queue.create_queue(stream_queue)
        
        try:
            while True:
                message = await self.message_queue.receive_message(
                    queue_name=stream_queue,
                    timeout_seconds=30  # 30 second timeout
                )
                
                if not message:
                    break
                
                chunk_data = message.payload
                await self.message_queue.acknowledge_message(message)
                
                # Check for stream end marker
                if chunk_data.get('stream_end', False):
                    break
                
                yield chunk_data
        finally:
            # Cleanup stream queue
            await self.message_queue.delete_queue(stream_queue)
    
    async def get_or_create_agent_instance(
        self,
        agent_id: str,
        session_id: Optional[str] = None
    ) -> AgentInstance:
        """Get or create an agent instance."""
        instance_key = f"{agent_id}#{session_id}" if session_id else agent_id
        
        async with self._instance_lock:
            # Check existing instance
            if instance_key in self._agent_instances:
                instance = self._agent_instances[instance_key]
                instance.update_activity()
                logger.debug(f"Reusing agent instance: {instance_key}")
                return instance
            
            # Load agent from repository
            async with self.uow:
                agent_id_vo = AgentId.from_string(agent_id)
                agent = await self.uow.agents.get_by_id(agent_id_vo)
                if not agent:
                    raise ValueError(f"Agent {agent_id} not found")
            
            # Create framework agent instance (stateless executor)
            framework_agent = self._framework.create_agent_executor()
            
            # Create managed instance
            instance = AgentInstance(
                agent_id=agent_id,
                session_id=session_id,
                agent=agent,
                framework_agent=framework_agent
            )
            
            self._agent_instances[instance_key] = instance
            logger.info(f"Created agent instance: {instance_key}")
            return instance
    
    async def destroy_agent_instance(self, agent_id: str, session_id: Optional[str] = None) -> bool:
        """Destroy an agent instance."""
        instance_key = f"{agent_id}#{session_id}" if session_id else agent_id
        
        async with self._instance_lock:
            if instance_key in self._agent_instances:
                instance = self._agent_instances[instance_key]
                
                # Cleanup framework agent
                try:
                    await instance.framework_agent.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up framework agent {instance_key}: {e}")
                
                # Remove from managed instances
                del self._agent_instances[instance_key]
                logger.info(f"Destroyed agent instance: {instance_key}")
                return True
        
        return False
    
    async def list_agent_instances(self) -> List[Dict[str, Any]]:
        """List all managed agent instances."""
        async with self._instance_lock:
            return [
                {
                    'instance_key': instance.instance_key,
                    'agent_id': instance.agent_id,
                    'session_id': instance.session_id,
                    'created_at': instance.created_at.isoformat(),
                    'last_activity': instance.last_activity.isoformat(),
                    'message_count': instance.message_count,
                    'is_active': instance.is_active
                }
                for instance in self._agent_instances.values()
            ]
    
    async def _task_worker(self, worker_id: str) -> None:
        """Task worker that processes messages from the task queue."""
        logger.info(f"Task worker {worker_id} started")
        
        while self._running:
            try:
                # Receive task from queue
                message = await self.message_queue.receive_message(
                    queue_name=self.TASK_QUEUE,
                    timeout_seconds=5
                )
                
                if not message:
                    continue
                
                # Parse task request
                task_request = AgentTaskRequest.from_dict(message.payload)
                logger.debug(f"Worker {worker_id} processing task {task_request.task_id}")
                
                try:
                    # Execute task
                    if task_request.task_type == TaskType.EXECUTE:
                        result = await self._execute_agent_task(task_request)
                    elif task_request.task_type == TaskType.STREAM_EXECUTE:
                        result = await self._execute_streaming_task(task_request)
                    else:
                        result = AgentTaskResult(
                            task_id=task_request.task_id,
                            agent_id=task_request.agent_id,
                            status=TaskStatus.FAILED,
                            error=f"Unsupported task type: {task_request.task_type}"
                        )
                    
                    # Send result
                    await self._send_task_result(message, result)
                    
                    # Acknowledge message
                    await self.message_queue.acknowledge_message(message)
                    
                except Exception as e:
                    logger.error(f"Task execution failed: {e}")
                    
                    # Send error result
                    error_result = AgentTaskResult(
                        task_id=task_request.task_id,
                        agent_id=task_request.agent_id,
                        status=TaskStatus.FAILED,
                        error=str(e)
                    )
                    await self._send_task_result(message, error_result)
                    
                    # Reject message
                    await self.message_queue.reject_message(message, requeue=False, reason=str(e))
            
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Task worker {worker_id} stopped")
    
    async def _execute_agent_task(self, task_request: AgentTaskRequest) -> AgentTaskResult:
        """Execute a regular agent task."""
        start_time = time.time()
        
        # Get agent instance
        instance = await self.get_or_create_agent_instance(
            task_request.agent_id,
            task_request.session_id
        )
        
        try:
            # Execute using framework agent
            response = await instance.framework_agent.execute(
                template_id=instance.agent.template_id,
                template_version=instance.agent.template_version or "v1.0.0",
                configuration=instance.agent.configuration,
                messages=task_request.messages,
                temperature=task_request.temperature,
                max_tokens=task_request.max_tokens,
                metadata={
                    # Agent static context
                    "agent_id": instance.agent_id,
                    "agent_name": instance.agent.name,
                    "template_id": instance.agent.template_id,
                    "template_version": instance.agent.template_version or "v1.0.0",
                    # Dynamic execution context
                    "session_id": task_request.session_id,
                    "user_id": task_request.user_id,
                    "task_id": task_request.task_id,
                    **(task_request.metadata or {})
                }
            )
            
            # Convert response
            processing_time = int((time.time() - start_time) * 1000)

            if response.success:
                status = TaskStatus.COMPLETED
            else:
                status = TaskStatus.FAILED
            
            return AgentTaskResult(
                task_id=task_request.task_id,
                agent_id=task_request.agent_id,
                status=status,
                message=response.message,
                error=response.error,
                finish_reason=response.finish_reason,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                processing_time_ms=processing_time,
                metadata={
                    "session_id": task_request.session_id,
                    "user_id": task_request.user_id,
                    "instance_key": instance.instance_key
                }
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return AgentTaskResult(
                task_id=task_request.task_id,
                agent_id=task_request.agent_id,
                status=TaskStatus.FAILED,
                error=str(e),
                processing_time_ms=processing_time
            )
    
    async def _execute_streaming_task(self, task_request: AgentTaskRequest) -> AgentTaskResult:
        """Execute a streaming agent task."""
        start_time = time.time()
        stream_queue = f"{self.STREAM_QUEUE_PREFIX}{task_request.task_id}"
        
        # Create stream queue
        await self.message_queue.create_queue(stream_queue)
        
        # Get agent instance
        instance = await self.get_or_create_agent_instance(
            task_request.agent_id,
            task_request.session_id
        )
        
        try:
            # Stream execution
            chunk_count = 0
            async for chunk in instance.framework_agent.stream_execute(
                template_id=instance.agent.template_id,
                template_version=instance.agent.template_version or "v1.0.0",
                configuration=instance.agent.configuration,
                messages=task_request.messages,
                temperature=task_request.temperature,
                max_tokens=task_request.max_tokens,
                metadata={
                    # Agent static context
                    "agent_id": instance.agent_id,
                    "agent_name": instance.agent.name,
                    "template_id": instance.agent.template_id,
                    "template_version": instance.agent.template_version or "v1.0.0",
                    # Dynamic execution context
                    "session_id": task_request.session_id,
                    "user_id": task_request.user_id,
                    "task_id": task_request.task_id,
                    **(task_request.metadata or {})
                }
            ):
                # Send chunk to stream queue
                chunk_data = {
                    "id": getattr(chunk, 'id', str(uuid.uuid4())),
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now(UTC).timestamp()),
                    "model": task_request.agent_id,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": getattr(chunk, 'content', '')},
                        "finish_reason": getattr(chunk, 'finish_reason', None)
                    }],
                    "chunk_index": chunk_count
                }
                
                await self.message_queue.send_message(
                    queue_name=stream_queue,
                    payload=chunk_data,
                    priority=MessagePriority.HIGH
                )
                
                chunk_count += 1
            
            # Send stream end marker
            await self.message_queue.send_message(
                queue_name=stream_queue,
                payload={"stream_end": True, "total_chunks": chunk_count},
                priority=MessagePriority.HIGH
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentTaskResult(
                task_id=task_request.task_id,
                agent_id=task_request.agent_id,
                status=TaskStatus.COMPLETED,
                message=f"Streaming completed with {chunk_count} chunks",
                finish_reason="stop",
                processing_time_ms=processing_time,
                metadata={
                    "stream_queue": stream_queue,
                    "chunk_count": chunk_count,
                    "session_id": task_request.session_id,
                    "user_id": task_request.user_id
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
            
            return AgentTaskResult(
                task_id=task_request.task_id,
                agent_id=task_request.agent_id,
                status=TaskStatus.FAILED,
                error=str(e),
                processing_time_ms=processing_time
            )
    
    async def _send_task_result(self, original_message: QueueMessage, result: AgentTaskResult) -> None:
        """Send task result to reply queue."""
        reply_to = original_message.reply_to or self.RESULT_QUEUE
        
        await self.message_queue.send_message(
            queue_name=reply_to,
            payload=result.to_dict(),
            correlation_id=original_message.correlation_id,
            metadata={
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
        
        async with self._instance_lock:
            for instance_key, instance in self._agent_instances.items():
                inactive_seconds = (now - instance.last_activity).total_seconds()
                
                if inactive_seconds > timeout_threshold:
                    instances_to_remove.append(instance_key)
        
        # Remove inactive instances
        for instance_key in instances_to_remove:
            try:
                agent_id = instance_key.split('#')[0]
                session_id = instance_key.split('#')[1] if '#' in instance_key else None
                await self.destroy_agent_instance(agent_id, session_id)
                logger.info(f"Cleaned up inactive instance: {instance_key}")
            except Exception as e:
                logger.error(f"Failed to cleanup instance {instance_key}: {e}")
        
        if instances_to_remove:
            logger.info(f"Cleaned up {len(instances_to_remove)} inactive agent instances")
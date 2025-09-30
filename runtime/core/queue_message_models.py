"""Internal Queue Message Models - Clean domain models for message queue communication.

These models represent internal domain concepts only, without external API format dependencies.
They are used for internal message queue communication between orchestrator and services.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time

class QueueMessageType(str, Enum):
    """Types of queue messages for internal communication."""
    STREAMING_CHUNK = "streaming_chunk"
    EXECUTION_RESULT = "execution_result"
    ERROR = "error"


class StreamingChunkQueueMessage(BaseModel):
    """Internal queue message for streaming chunks - pure domain concepts.

    This contains only internal domain concepts for streaming communication
    between orchestrator and services, without external API format dependencies.
    """
    message_type: QueueMessageType = Field(default=QueueMessageType.STREAMING_CHUNK, frozen=True)

    # Core domain identifiers
    message_id: str = Field(description="Internal message identifier")
    task_id: str = Field(description="Internal task identifier for stateful conversations")
    agent_id: str = Field(description="Agent identifier")
    context_id: Optional[str] = Field(default=None, description="Optional context identifier")

    # Streaming content data
    content: str = Field(default="", description="Streaming content chunk")
    chunk_index: int = Field(default=0, description="Sequential chunk index")
    finish_reason: Optional[str] = Field(default=None, description="Reason for stream completion")

    # System metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional system metadata")
    timestamp: float = Field(description="Message timestamp")

    class Config:
        frozen = True  # Immutable for thread safety


class ExecutionResultQueueMessage(BaseModel):
    """Internal queue message for execution results - pure domain concepts.

    This contains only internal domain concepts for execution results
    communication between orchestrator and services, without external API format dependencies.
    """
    message_type: QueueMessageType = Field(default=QueueMessageType.EXECUTION_RESULT, frozen=True)

    # Core domain identifiers
    message_id: str = Field(description="Internal message identifier")
    task_id: str = Field(description="Internal task identifier for stateful conversations")
    agent_id: str = Field(description="Agent identifier")
    context_id: Optional[str] = Field(default=None, description="Optional context identifier")

    # Execution results
    success: bool = Field(description="Whether execution succeeded")
    content: str = Field(default="", description="Final execution content")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    # Performance metrics
    processing_time_ms: int = Field(default=0, description="Total processing time in milliseconds")
    prompt_tokens: int = Field(default=0, description="Prompt tokens used")
    completion_tokens: int = Field(default=0, description="Completion tokens used")

    # System metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional system metadata")
    timestamp: float = Field(description="Message timestamp")

    class Config:
        frozen = True  # Immutable for thread safety


class ErrorQueueMessage(BaseModel):
    """Internal queue message for errors - pure domain concepts.

    This contains only internal domain concepts for error communication
    between orchestrator and services, without external API format dependencies.
    """
    message_type: QueueMessageType = Field(default=QueueMessageType.ERROR, frozen=True)

    # Core domain identifiers
    message_id: str = Field(description="Internal message identifier")
    task_id: str = Field(description="Internal task identifier for stateful conversations")
    agent_id: str = Field(description="Agent identifier")
    context_id: Optional[str] = Field(default=None, description="Optional context identifier")

    # Error information
    error: str = Field(description="Error message")
    error_type: Optional[str] = Field(default=None, description="Error type/classification")

    # Context information
    original_message_type: Optional[QueueMessageType] = Field(default=None, description="Type of message that failed")

    # System metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional system metadata")
    timestamp: float = Field(description="Message timestamp")

    class Config:
        frozen = True  # Immutable for thread safety


# Union type for all queue payload types
QueuePayloadType = StreamingChunkQueueMessage | ExecutionResultQueueMessage | ErrorQueueMessage


def create_streaming_chunk_message(
    message_id: str,
    task_id: str,
    agent_id: str,
    content: str,
    chunk_index: int = 0,
    finish_reason: Optional[str] = None,
    context_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> StreamingChunkQueueMessage:
    """Create a streaming chunk queue message with timestamp."""
    return StreamingChunkQueueMessage(
        message_id=message_id,
        task_id=task_id,
        agent_id=agent_id,
        content=content,
        chunk_index=chunk_index,
        finish_reason=finish_reason,
        context_id=context_id,
        metadata=metadata or {},
        timestamp=time.time()
    )


def create_execution_result_message(
    message_id: str,
    task_id: str,
    agent_id: str,
    success: bool,
    content: str = "",
    error: Optional[str] = None,
    processing_time_ms: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    context_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ExecutionResultQueueMessage:
    """Create an execution result queue message with timestamp."""
    return ExecutionResultQueueMessage(
        message_id=message_id,
        task_id=task_id,
        agent_id=agent_id,
        success=success,
        content=content,
        error=error,
        processing_time_ms=processing_time_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        context_id=context_id,
        metadata=metadata or {},
        timestamp=time.time()
    )


def create_error_message(
    message_id: str,
    task_id: str,
    agent_id: str,
    error: str,
    error_type: Optional[str] = None,
    original_message_type: Optional[QueueMessageType] = None,
    context_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ErrorQueueMessage:
    """Create an error queue message with timestamp."""
    return ErrorQueueMessage(
        message_id=message_id,
        task_id=task_id,
        agent_id=agent_id,
        error=error,
        error_type=error_type,
        original_message_type=original_message_type,
        context_id=context_id,
        metadata=metadata or {},
        timestamp=time.time()
    )
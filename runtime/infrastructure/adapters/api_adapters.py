"""API Adapters - Convert between external API formats and internal domain models.

These adapters handle the conversion between external API formats (OpenAI, A2A, etc.)
and our internal domain models, keeping the core domain clean from external dependencies.
"""

import time
from typing import Any, Optional, Union

from ...core.queue_message_models import (
    QueuePayloadType,
    StreamingChunkQueueMessage,
    ExecutionResultQueueMessage,
    ErrorQueueMessage,
    QueueMessageType,
)
from ...core.executors import StreamingChunk, ExecutionResult


class OpenAIAdapter:
    """Adapter for OpenAI API format conversion.

    Converts between OpenAI API format and our internal domain models.
    Only used at API boundaries, not in internal domain logic.
    """

    @staticmethod
    def streaming_chunk_to_openai_format(chunk: StreamingChunkQueueMessage) -> dict[str, Any]:
        """Convert internal streaming chunk to OpenAI API format."""
        result = {
            "id": f"chatcmpl-{chunk.message_id}",
            "object": "chat.completion.chunk",
            "created": int(chunk.timestamp),
            "model": "agent",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": chunk.content
                    },
                    "finish_reason": chunk.finish_reason
                }
            ]
        }

        # Add system metadata if present
        if chunk.metadata:
            result["system_metadata"] = chunk.metadata

        return result

    @staticmethod
    def openai_chunk_to_streaming_chunk(openai_chunk: dict[str, Any]) -> StreamingChunkQueueMessage:
        """Convert OpenAI API chunk to internal streaming chunk.

        Extracts internal domain concepts from OpenAI format.
        """
        # Extract core identifiers from OpenAI format
        openai_id = openai_chunk.get("id", "")
        message_id = openai_id.replace("chatcmpl-", "") if openai_id.startswith("chatcmpl-") else openai_id

        # Extract content from OpenAI choices/delta structure
        choices = openai_chunk.get("choices", [])
        content = ""
        finish_reason = None

        if choices:
            choice = choices[0]
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            finish_reason = choice.get("finish_reason")

        # Extract system metadata
        metadata = openai_chunk.get("system_metadata", {})
        metadata.update({
            "openai_object": openai_chunk.get("object"),
            "openai_model": openai_chunk.get("model"),
        })

        return StreamingChunkQueueMessage(
            message_id=message_id,
            task_id=openai_chunk.get("task_id", ""),
            agent_id=openai_chunk.get("agent_id", ""),
            context_id=openai_chunk.get("context_id"),
            content=content,
            chunk_index=openai_chunk.get("chunk_index", 0),
            finish_reason=finish_reason,
            metadata=metadata,
            timestamp=time.time()
        )

    @staticmethod
    def execution_result_to_openai_format(result: ExecutionResultQueueMessage) -> dict[str, Any]:
        """Convert internal execution result to OpenAI API format."""
        return {
            "id": f"chatcmpl-{result.message_id}",
            "object": "chat.completion",
            "created": int(result.timestamp),
            "model": "agent",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.content
                    },
                    "finish_reason": "stop" if result.success else "length"
                }
            ],
            "usage": {
                # Use actual prompt and completion token counts if available in metadata, otherwise split evenly as a fallback.
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.prompt_tokens + result.completion_tokens
            }
        }

    @staticmethod
    def openai_completion_to_execution_result(openai_completion: dict[str, Any]) -> ExecutionResultQueueMessage:
        """Convert OpenAI completion to internal execution result."""
        openai_id = openai_completion.get("id", "")
        message_id = openai_id.replace("chatcmpl-", "") if openai_id.startswith("chatcmpl-") else openai_id

        choices = openai_completion.get("choices", [])
        content = ""
        success = True

        if choices:
            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            finish_reason = choice.get("finish_reason")
            success = finish_reason in ["stop", "length"]

        usage = openai_completion.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return ExecutionResultQueueMessage(
            message_id=message_id,
            task_id=openai_completion.get("task_id", ""),
            agent_id=openai_completion.get("agent_id", ""),
            context_id=openai_completion.get("context_id"),
            success=success,
            content=content,
            processing_time_ms=int((time.time() - openai_completion.get("created", time.time())) * 1000),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            metadata={
                "openai_object": openai_completion.get("object"),
                "openai_model": openai_completion.get("model"),
            },
            timestamp=time.time()
        )


class A2AAdapter:
    """Adapter for A2A (Agent-to-Agent) protocol format conversion.

    Converts between A2A protocol format and our internal domain models.
    Only used at API boundaries, not in internal domain logic.
    """

    @staticmethod
    def streaming_chunk_to_a2a_format(chunk: StreamingChunkQueueMessage) -> dict[str, Any]:
        """Convert internal streaming chunk to A2A protocol format."""
        return {
            "message_id": chunk.message_id,
            "task_id": chunk.task_id,
            "agent_id": chunk.agent_id,
            "context_id": chunk.context_id,
            "type": "streaming_chunk",
            "content": chunk.content,
            "chunk_index": chunk.chunk_index,
            "finish_reason": chunk.finish_reason,
            "metadata": chunk.metadata,
            "timestamp": chunk.timestamp
        }

    @staticmethod
    def a2a_chunk_to_streaming_chunk(a2a_chunk: dict[str, Any]) -> StreamingChunkQueueMessage:
        """Convert A2A protocol chunk to internal streaming chunk."""
        return StreamingChunkQueueMessage(
            message_id=a2a_chunk["message_id"],
            task_id=a2a_chunk["task_id"],
            agent_id=a2a_chunk["agent_id"],
            context_id=a2a_chunk.get("context_id"),
            content=a2a_chunk["content"],
            chunk_index=a2a_chunk.get("chunk_index", 0),
            finish_reason=a2a_chunk.get("finish_reason"),
            metadata=a2a_chunk.get("metadata", {}),
            timestamp=a2a_chunk.get("timestamp", time.time())
        )

    @staticmethod
    def execution_result_to_a2a_format(result: ExecutionResultQueueMessage) -> dict[str, Any]:
        """Convert internal execution result to A2A protocol format."""
        return {
            "message_id": result.message_id,
            "task_id": result.task_id,
            "agent_id": result.agent_id,
            "context_id": result.context_id,
            "type": "execution_result",
            "success": result.success,
            "content": result.content,
            "error": result.error,
            "processing_time_ms": result.processing_time_ms,
            "metadata": result.metadata,
            "timestamp": result.timestamp
        }

    @staticmethod
    def a2a_result_to_execution_result(a2a_result: dict[str, Any]) -> ExecutionResultQueueMessage:
        """Convert A2A protocol result to internal execution result."""
        return ExecutionResultQueueMessage(
            message_id=a2a_result["message_id"],
            task_id=a2a_result["task_id"],
            agent_id=a2a_result["agent_id"],
            context_id=a2a_result.get("context_id"),
            success=a2a_result["success"],
            content=a2a_result.get("content", ""),
            error=a2a_result.get("error"),
            processing_time_ms=a2a_result.get("processing_time_ms", 0),
            metadata=a2a_result.get("metadata", {}),
            timestamp=a2a_result.get("timestamp", time.time())
        )


class DomainModelAdapter:
    """Adapter for converting between queue messages and domain models.

    Converts between our internal queue message models and core domain models
    (StreamingChunk, ExecutionResult) used by the application layer.
    """

    @staticmethod
    def streaming_chunk_to_domain(chunk: StreamingChunkQueueMessage) -> StreamingChunk:
        """Convert streaming chunk queue message to domain model."""
        return StreamingChunk(
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            finish_reason=chunk.finish_reason,
            message_id=chunk.message_id,
            task_id=chunk.task_id,
            agent_id=chunk.agent_id,
            context_id=chunk.context_id,
            metadata=chunk.metadata
        )
    
    @staticmethod
    def execution_result_to_domain(result: ExecutionResultQueueMessage) -> ExecutionResult:
        """Convert execution result queue message to domain model."""
        return ExecutionResult(
            success=result.success,
            message=result.content,
            error=result.error,
            processing_time_ms=result.processing_time_ms,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            message_id=result.message_id,
            task_id=result.task_id,
            agent_id=result.agent_id,
            context_id=result.context_id,
            metadata=result.metadata
        )

    @staticmethod
    def stream_chunk_from_domain(domain_model: StreamingChunk) -> StreamingChunkQueueMessage:
        """Convert domain model to streaming chunk queue message."""
        return StreamingChunkQueueMessage(
            message_id=domain_model.message_id or "",
            task_id=domain_model.task_id or "",
            agent_id=domain_model.agent_id or "",
            context_id=domain_model.context_id,
            content=domain_model.content,
            chunk_index=domain_model.chunk_index,
            finish_reason=domain_model.finish_reason,
            metadata=domain_model.metadata or {},
            timestamp=time.time()
        )
    
    @staticmethod
    def execution_result_from_domain(domain_model: ExecutionResult) -> ExecutionResultQueueMessage:
        """Convert domain model to execution result queue message."""
        return ExecutionResultQueueMessage(
            message_id=domain_model.message_id or "",
            task_id=domain_model.task_id or "",
            agent_id=domain_model.agent_id or "",
            context_id=domain_model.context_id,
            success=domain_model.success,
            content=domain_model.message or "",
            error=domain_model.error,
            processing_time_ms=domain_model.processing_time_ms,
            prompt_tokens=domain_model.prompt_tokens,
            completion_tokens=domain_model.completion_tokens,
            metadata=domain_model.metadata or {},
            timestamp=time.time()
        )

class APIAdapterRegistry:
    """Registry for API adapters, allowing easy extension for new protocols."""

    def __init__(self):
        self._adapters = {
            "openai": OpenAIAdapter(),
            "a2a": A2AAdapter(),
        }
        self._domain_adapter = DomainModelAdapter()

    def register_adapter(self, protocol: str, adapter):
        """Register a new API adapter for a protocol."""
        self._adapters[protocol.lower()] = adapter

    def get_adapter(self, protocol: str):
        """Get adapter for a specific protocol."""
        adapter = self._adapters.get(protocol.lower())
        if not adapter:
            raise ValueError(f"No adapter registered for protocol: {protocol}")
        return adapter

    @property
    def domain_adapter(self) -> DomainModelAdapter:
        """Get the domain model adapter."""
        return self._domain_adapter

    @property
    def supported_protocols(self) -> list[str]:
        """Get list of supported protocols."""
        return list(self._adapters.keys())


# Global registry instance
api_adapter_registry = APIAdapterRegistry()
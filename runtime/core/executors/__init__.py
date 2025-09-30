"""Core executor interfaces and types for the runtime."""

from .interfaces import (
    ExecutionResult,
    StreamingChunk,
    AgentExecutorInterface,
    FrameworkExecutorInterface,
    ExecutionContext
)

__all__ = [
    "ExecutionResult",
    "StreamingChunk", 
    "AgentExecutorInterface",
    "FrameworkExecutorInterface",
    "ExecutionContext"
]


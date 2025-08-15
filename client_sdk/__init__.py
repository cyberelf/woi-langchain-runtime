"""LangChain Agent Runtime Client SDK.

This package provides a high-level client interface for interacting with
the LangChain Agent Runtime, including template discovery, agent management,
and interactive chat sessions.

Example usage:
    >>> from client_sdk import create_client, RuntimeClient
    >>> 
    >>> # Using convenience function
    >>> client = await create_client()
    >>> templates = await client.list_templates()
    >>> 
    >>> # Using context manager
    >>> async with RuntimeClientContext() as client:
    >>>     agents = await client.list_agents()
"""

from .client import RuntimeClient, RuntimeClientContext, create_client
from .models import (
    AgentInfo,
    ChatMessage,
    ChatChoice,
    ChatCompletionChoice,  # Alias
    ChatCompletionResponse,
    ChatCompletionChunk,
    ChatUsage,
    MessageRole,
    TemplateInfo,
    RuntimeStatus,
    CreateAgentRequest,
)

__version__ = "1.0.0"

__all__ = [
    # Main client classes
    "RuntimeClient",
    "RuntimeClientContext", 
    "create_client",
    
    # Models
    "AgentInfo",
    "ChatMessage",
    "ChatChoice",
    "ChatCompletionChoice",  # Alias
    "ChatCompletionResponse",
    "ChatCompletionChunk",
    "ChatUsage",
    "MessageRole",
    "TemplateInfo",
    "RuntimeStatus",
    "CreateAgentRequest",
]

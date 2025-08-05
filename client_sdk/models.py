"""Client SDK data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


# Core Data Models
class MessageRole(str, Enum):
    """Enumerator for the role of a message in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: MessageRole
    content: str


# API Request Models
class AgentCreateRequest(BaseModel):
    """Request model for creating a new agent."""
    id: str = Field(..., description="Unique identifier for the agent.")
    name: str = Field(..., description="A human-readable name for the agent.")
    description: Optional[str] = Field(None, description="A brief description of the agent's purpose.")
    template_id: str = Field(..., description="The ID of the template to use for this agent.")
    template_version: Optional[str] = Field(None, description="The version of the aplate to use.")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration overrides for the agent.")


# API Response Models
@dataclass
class TemplateInfo:
    """Information about an available template."""
    template_id: str
    template_name: str
    version: str
    framework: str
    description: str
    metadata: Dict[str, Any]


@dataclass
class AgentInfo:
    """Information about an existing agent."""
    agent_id: str
    name: str
    description: str
    template_id: str
    template_version: str
    status: str
    created_at: str


class ChatCompletionChoice(BaseModel):
    """A single choice in a chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """Response model for a non-streaming chat completion."""
    id: str
    choices: List[ChatCompletionChoice]
    created: int
    model: str
    object: str = "chat.completion"
    system_fingerprint: str
    usage: Dict[str, int]


class ChatCompletionChunkChoice(BaseModel):
    """A single choice in a streaming chat completion chunk."""
    delta: ChatMessage
    finish_reason: Optional[str] = None
    index: int


class ChatCompletionChunk(BaseModel):
    """A chunk of a streaming chat completion response."""
    id: str
    choices: List[ChatCompletionChunkChoice]
    created: int
    model: str
    object: str = "chat.completion.chunk"
    system_fingerprint: str


# Status Enums
class RuntimeStatus(Enum):
    """Runtime connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


__all__ = [
    "AgentCreateRequest",
    "AgentInfo",
    "ChatMessage",
    "ChatCompletionResponse",
    "ChatCompletionChunk",
    "MessageRole",
    "TemplateInfo",
    "RuntimeStatus",
]

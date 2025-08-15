"""Client SDK data models."""

from dataclasses import dataclass
from typing import Optional
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
class CreateAgentRequest(BaseModel):
    """Request model for creating a new agent - matches API specification."""
    # Core fields - following API specification
    id: str = Field(..., description="Agent line ID (logical identifier)")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    avatar_url: Optional[str] = Field(None, description="Agent avatar URL")
    type: str = Field(..., description="Agent type")
    
    # Template fields - following API specification
    template_id: str = Field(..., description="Template type identifier")
    template_version: Optional[str] = Field(None, description="The version of the template to use.")
    template_version_id: str = Field(..., description="Template version string")
    
    # Configuration fields
    system_prompt: Optional[str] = Field(None, description="System prompt")
    conversation_config: Optional[dict] = Field(None, description="Conversation configuration")
    toolsets: Optional[list[str]] = Field(None, description="Available toolsets")
    llm_config_id: Optional[str] = Field(None, description="LLM configuration ID")
    template_config: Optional[dict] = Field(None, description="Template configuration")

    # Metadata - following API specification
    agent_line_id: str = Field(..., description="Agent line ID")
    version_type: Optional[str] = Field("beta", description="Version type: beta or release (default: beta)")
    version_number: Optional[str] = Field("v1", description="Version number: 'v1', 'v2', etc. (default: v1)")
    owner_id: str = Field(..., description="Agent owner ID for beta access control")
    status: Optional[str] = Field(
        "draft", 
        description="Agent status: draft, submitted, pending, published, revoked (default: draft)"
    )

# Backward compatibility alias
AgentCreateRequest = CreateAgentRequest


# API Response Models
@dataclass
class TemplateInfo:
    """Information about an available template."""
    template_id: str
    template_name: str
    version: str
    framework: str
    description: str
    metadata: dict


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


class ChatChoice(BaseModel):
    """A single choice in a chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

# Alias for backward compatibility
ChatCompletionChoice = ChatChoice


class ChatUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Response model for a non-streaming chat completion."""
    id: str
    choices: list[ChatChoice]
    created: int
    model: str
    object: str = "chat.completion"
    system_fingerprint: Optional[str] = None
    usage: ChatUsage


class ChatCompletionChunkChoice(BaseModel):
    """A single choice in a streaming chat completion chunk."""
    delta: ChatMessage
    finish_reason: Optional[str] = None
    index: int


class ChatCompletionChunk(BaseModel):
    """A chunk of a streaming chat completion response."""
    id: str
    choices: list[ChatCompletionChunkChoice]
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
    "CreateAgentRequest",
    "AgentCreateRequest",  # Backward compatibility alias
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
]

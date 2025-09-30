"""Client SDK data models."""

from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict
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
    """Request model for creating a new agent - matches server API specification exactly."""
    # Core fields - following API specification
    id: str = Field(..., description="Agent line ID (logical identifier)")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    avatar_url: Optional[str] = Field(None, description="Agent avatar URL")
    type: str = Field(..., description="Agent type")
    
    # Template fields - following API specification
    template_id: str = Field(..., description="Template type identifier")
    template_version_id: Optional[str] = Field("1.0.0", description="Template version string")
    
    # Configuration fields
    system_prompt: Optional[str] = Field(None, description="System prompt")
    conversation_config: Optional[dict] = Field(None, description="Conversation configuration")
    toolsets: Optional[list[str]] = Field(None, description="Available toolsets")
    llm_config_id: Optional[str] = Field(None, description="LLM configuration ID")
    template_config: Optional[dict] = Field(None, description="Template configuration")

    # Metadata - following API specification
    agent_line_id: Optional[str] = Field(None, description="Agent line ID")
    version_type: Optional[str] = Field("beta", description="Version type: beta or release (default: beta)")
    version_number: Optional[str] = Field("v1", description="Version number: 'v1', 'v2', etc. (default: v1)")
    owner_id: Optional[str] = Field(None, description="Agent owner ID for beta access control")
    status: Optional[str] = Field(
        "draft", 
        description="Agent status: draft, submitted, pending, published, revoked (default: draft)"
    )
    
    @model_validator(mode="before")
    @classmethod
    def set_agent_line_id_default(cls, values):
        """Set agent_line_id to id if not provided - matches server behavior."""
        if values.get("agent_line_id") is None and "id" in values:
            values["agent_line_id"] = values["id"]
        return values

# Backward compatibility alias
AgentCreateRequest = CreateAgentRequest


# API Response Models
@dataclass
class TemplateInfo:
    """Information about an available template."""
    id: str
    name: str
    version: str
    framework: str
    description: str
    config: list[dict]


class AgentInfo(BaseModel):
    """Information about an existing agent - matches server AgentResponse structure."""
    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    template_id: str = Field(..., description="Template identifier")
    template_version: Optional[str] = Field(None, description="Template version")
    status: str = Field(..., description="Agent status")
    configuration: dict = Field(..., description="Agent configuration")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")
    metadata: dict = Field(..., description="Agent metadata")

    @property
    def agent_id(self) -> str:
        """Backward compatibility property for agent_id."""
        return self.id

    @property 
    def description(self) -> Optional[str]:
        """Extract description from metadata for backward compatibility."""
        return self.metadata.get("description")

    model_config = ConfigDict(extra="forbid")


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
    metadata: Optional[dict] = Field(None, description="Additional execution metadata")


class StreamingChunkDelta(BaseModel):
    """Delta content for streaming chunks - OpenAI API compliant."""
    role: Optional[str] = None  # Only present in first chunk
    content: Optional[str] = None  # Incremental content


class StreamingChunkChoice(BaseModel):
    """A single choice in a streaming chat completion chunk - OpenAI API compliant."""
    index: int
    delta: StreamingChunkDelta
    finish_reason: Optional[str] = None


class StreamingChunk(BaseModel):
    """A chunk of a streaming chat completion response - OpenAI API compliant."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    system_fingerprint: Optional[str] = None
    choices: list[StreamingChunkChoice]


# Backward compatibility aliases
ChatCompletionChunkChoice = StreamingChunkChoice
ChatCompletionChunk = StreamingChunk


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
    "ChatUsage",
    "MessageRole",
    "TemplateInfo",
    "RuntimeStatus",
    # New OpenAI-compliant streaming models
    "StreamingChunk",
    "StreamingChunkChoice", 
    "StreamingChunkDelta",
    # Backward compatibility aliases
    "ChatCompletionChunk",
    "ChatCompletionChunkChoice",
]

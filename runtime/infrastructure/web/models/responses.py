"""Web layer response models - Infrastructure layer."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from ....domain.value_objects.chat_message import MessageRole


class AgentResponse(BaseModel):
    """HTTP response model for agents."""
    
    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    template_id: str = Field(..., description="Template identifier")
    template_version: Optional[str] = Field(None, description="Template version")
    status: str = Field(..., description="Agent status")
    configuration: Dict[str, Any] = Field(..., description="Agent configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: Dict[str, Any] = Field(..., description="Agent metadata")
    
    class Config:
        extra = "forbid"


class ChatMessageResponse(BaseModel):
    """HTTP response model for chat messages."""
    
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Dict[str, Any] = Field(..., description="Message metadata")
    
    class Config:
        extra = "forbid"


class ChatSessionResponse(BaseModel):
    """HTTP response model for chat sessions."""
    
    id: str = Field(..., description="Session identifier")
    agent_id: str = Field(..., description="Agent identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    message_count: int = Field(..., description="Number of messages in session")
    metadata: Dict[str, Any] = Field(..., description="Session metadata")
    
    class Config:
        extra = "forbid"


class ChatChoice(BaseModel):
    """OpenAI-compatible chat choice."""
    
    index: int = Field(..., description="Choice index")
    message: ChatMessageResponse = Field(..., description="Response message")
    finish_reason: str = Field(..., description="Reason for completion finish")
    
    class Config:
        extra = "forbid"


class ChatUsage(BaseModel):
    """OpenAI-compatible usage statistics."""
    
    prompt_tokens: int = Field(..., description="Number of prompt tokens")
    completion_tokens: int = Field(..., description="Number of completion tokens")
    total_tokens: int = Field(..., description="Total number of tokens")
    
    class Config:
        extra = "forbid"


class ExecuteAgentResponse(BaseModel):
    """HTTP response model for agent execution.
    
    OpenAI-compatible chat completion response.
    """
    
    id: str = Field(..., description="Response identifier")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Agent ID (model)")
    choices: List[ChatChoice] = Field(..., description="Response choices")
    usage: ChatUsage = Field(..., description="Token usage")
    
    class Config:
        extra = "forbid"


class StreamingChunk(BaseModel):
    """OpenAI-compatible streaming chunk."""
    
    id: str = Field(..., description="Response identifier")
    object: str = Field("chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Agent ID (model)")
    choices: List[Dict[str, Any]] = Field(..., description="Streaming choices")
    
    class Config:
        extra = "forbid"


class ErrorResponse(BaseModel):
    """HTTP error response."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    
    class Config:
        extra = "forbid"


class HealthResponse(BaseModel):
    """HTTP health check response."""
    
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Application version")
    components: Dict[str, str] = Field(..., description="Component health status")
    
    class Config:
        extra = "forbid"
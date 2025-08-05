"""Web layer request models - Infrastructure layer."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ....domain.value_objects.chat_message import MessageRole


class CreateAgentRequest(BaseModel):
    """HTTP request model for creating agents.
    
    Infrastructure layer model that handles HTTP/JSON serialization.
    Maps to domain command objects.
    """
    
    name: str = Field(..., description="Agent name")
    template_id: str = Field(..., description="Template identifier")
    template_version: Optional[str] = Field(None, description="Template version")
    configuration: Dict[str, Any] = Field(..., description="Agent configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        extra = "forbid"


class ChatMessageRequest(BaseModel):
    """HTTP request model for chat messages."""
    
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    
    class Config:
        extra = "forbid"


class ExecuteAgentRequest(BaseModel):
    """HTTP request model for executing agents.
    
    OpenAI-compatible chat completion request.
    """
    
    model: str = Field(..., description="Agent ID (OpenAI model field)")
    messages: List[ChatMessageRequest] = Field(..., description="Conversation messages")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Enable streaming response")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Request metadata including session_id, user_id")
    
    class Config:
        extra = "forbid"
    
    def get_session_id(self) -> Optional[str]:
        """Extract session ID from metadata."""
        if self.metadata:
            return self.metadata.get("session_id")
        return None
    
    def get_user_id(self) -> Optional[str]:
        """Extract user ID from metadata."""
        if self.metadata:
            return self.metadata.get("user_id")
        return None


class GetAgentRequest(BaseModel):
    """HTTP request model for getting agent."""
    
    agent_id: str = Field(..., description="Agent identifier")
    
    class Config:
        extra = "forbid"


class ListAgentsRequest(BaseModel):
    """HTTP request model for listing agents."""
    
    template_id: Optional[str] = Field(None, description="Filter by template ID")
    active_only: bool = Field(False, description="Only return active agents")
    limit: Optional[int] = Field(None, gt=0, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    
    class Config:
        extra = "forbid"
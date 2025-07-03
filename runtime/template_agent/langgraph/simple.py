"""Simple Test Agent Template - No external dependencies."""

import time
import uuid
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from runtime.models import (
    AgentCreateRequest,
    ChatChoice,
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    ChatUsage,
    FinishReason,
    MessageRole,
)
from runtime.template_agent.base import BaseAgentTemplate, ValidationResult


class ResponseStyle(str, Enum):
    """Response style options."""
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"


class SimpleTestAgentConfig(BaseModel):
    """Configuration for Simple Test Agent."""
    response_prefix: str = Field(
        default="Test: ",
        description="Prefix for test responses",
        min_length=1,
        max_length=50
    )
    response_style: ResponseStyle = Field(
        default=ResponseStyle.FRIENDLY,
        description="Style of response to generate"
    )

class SimpleTestAgent(BaseAgentTemplate):
    """Simple test agent template for validation - no external dependencies."""
    
    # Template metadata (class variables)
    template_name: str = "Simple Test Agent"
    template_id: str = "simple-test"
    template_version: str = "1.0.0"
    template_description: str = "Simple test agent for system validation"
    framework: str = "test"
    
    # Configuration schema (class variables)
    config_schema: type[BaseModel] = SimpleTestAgentConfig
    
    def __init__(self, agent_data: AgentCreateRequest):
        """Initialize the simple test agent."""
        super().__init__(agent_data)
        
        # Extract configuration
        self.response_prefix = self.template_config.get("response_prefix", "Test: ")
    
    def _build_graph(self):
        """Build the execution graph for simple test agent."""
        # Simple test agent doesn't need a complex graph
        # Return None for simplicity
        return None
    
    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> ValidationResult:
        """Validate template configuration."""
        try:
            cls.config_schema.model_validate(config)
            return ValidationResult(valid=True, errors=[], warnings=[])
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)], warnings=[])
    
    async def execute(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """Execute the simple test agent."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        # Create simple test response
        if messages:
            last_message = messages[-1]
            response_content = f"{self.response_prefix}Echo: {last_message.content}"
        else:
            response_content = f"{self.response_prefix}Hello! This is a test response."
        
        return ChatCompletionResponse(
            id=completion_id,
            object="chat.completion",
            created=int(start_time),
            model=self.id,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=response_content,
                    ),
                    finish_reason=FinishReason.STOP,
                ),
            ],
            usage=ChatUsage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
            ),
        )
    
    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Execute the simple test agent with streaming response."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        # Create simple test response
        if messages:
            last_message = messages[-1]
            response_content = f"{self.response_prefix}Stream Echo: {last_message.content}"
        else:
            response_content = f"{self.response_prefix}Stream Hello! This is a test response."
        
        # Simulate streaming by yielding word by word
        words = response_content.split()
        for i, word in enumerate(words):
            chunk = ChatCompletionChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=self.id,
                choices=[
                    {
                        "index": 0,
                        "delta": {"content": word + " " if i < len(words) - 1 else word},
                        "finish_reason": None if i < len(words) - 1 else "stop",
                    },
                ],
            )
            yield chunk 
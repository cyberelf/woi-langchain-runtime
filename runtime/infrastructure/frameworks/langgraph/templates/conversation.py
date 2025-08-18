"""Conversation Agent Template - Simple conversational AI template."""

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from langgraph.graph.state import CompiledStateGraph

# Updated imports for DDD structure
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.infrastructure.web.models.responses import (
    ChatChoice,
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatUsage,
)
from runtime.infrastructure.frameworks.langgraph.llm.service import (
    get_langgraph_llm_service,
)
from runtime.templates.base import BaseAgentTemplate

# Clean DDD imports
# FinishReason constants
FINISH_REASON_STOP = "stop"

class ValidationResult:
    """Validation result for framework operations."""
    def __init__(self, valid: bool, errors: list = None):
        self.valid = valid
        self.errors = errors or []
from .base import BaseLangGraphAgent


class ConversationAgentConfig(BaseModel):
    """Conversation agent configuration."""

    max_history: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of messages to keep in conversation history",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for response generation",
    )

    model_config = ConfigDict(extra="forbid")


class ConversationAgent(BaseAgentTemplate, BaseLangGraphAgent):
    """Simple conversation agent template using direct LLM calls."""

    # Template metadata (class variables)
    template_name: str = "Conversation Agent"
    template_id: str = "conversation"
    template_version: str = "1.0.0"
    template_description: str = "Simple conversational AI for general chat interactions"
    framework: str = "langchain"

    # Configuration schema (class variables)
    config_schema: dict[str, Any] = {
        "max_history": {
            "type": "integer",
            "default": 10,
            "minimum": 1,
            "maximum": 100,
            "description": "Maximum number of messages to keep in conversation history",
            "order": 0,
        },
        "temperature": {
            "type": "number",
            "default": 0.7,
            "minimum": 0.0,
            "maximum": 2.0,
            "description": "LLM temperature for response generation",
            "order": 1,
        },
    }

    def __init__(
        self, 
        configuration: dict[str, Any], 
        metadata: Optional[dict[str, Any]] = None, 
        llm_service=None, 
        toolset_service=None
    ):
        """Initialize the conversation agent."""
        super().__init__(configuration, metadata, llm_service, toolset_service)
        self._graph: CompiledStateGraph | None = None
        # Extract configuration from the configuration dict
        self.max_history = self.template_config.get("max_history", 10)
        self.temperature = self.template_config.get("temperature", 0.7)

        # Conversation state
        self.conversation_history: list[ChatMessage] = []

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> ValidationResult:
        """Validate template configuration."""
        errors = []
        warnings = []

        # Validate max_history
        max_history = config.get("max_history", 10)
        if not isinstance(max_history, int) or max_history < 1:
            errors.append("max_history must be a positive integer")
        elif max_history > 100:
            warnings.append("max_history > 100 may impact performance")

        # Validate temperature
        temperature = config.get("temperature", 0.7)
        if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
            errors.append("temperature must be between 0 and 2")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    async def execute(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """Execute the conversation agent."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        # Use provided temperature or default
        temp = temperature if temperature is not None else self.temperature

        # Prepare messages with system prompt
        conversation_messages = []

        # Add system message if we have a system prompt
        if self.system_prompt:
            conversation_messages.append(
                ChatMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            )

        # Add conversation history (limited by max_history)
        if self.conversation_history:
            recent_history = self.conversation_history[-self.max_history :]
            conversation_messages.extend(recent_history)

        # Add current messages
        conversation_messages.extend(messages)

        try:
            # Call LLM
            llm_client = await self.get_llm_client()
            response = await llm_client.ainvoke(conversation_messages)

            # Extract response content from LangChain response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)

            # Update conversation history
            self.conversation_history.extend(messages)
            self.conversation_history.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=content),
            )

            # Trim history if needed
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history :]

            # Calculate metrics
            total_time = time.time() - start_time

            # Create response
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
                            content=content,
                        ),
                        finish_reason=FINISH_REASON_STOP,
                    ),
                ],
                usage=ChatUsage(
                    prompt_tokens=0,  # LangChain doesn't provide token counts by default
                    completion_tokens=0,
                    total_tokens=0,
                ),
            )

        except Exception as e:
            raise RuntimeError(f"Conversation execution failed: {e}")

    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Execute the conversation agent with streaming response."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        # Use provided temperature or default
        temp = temperature if temperature is not None else self.temperature

        # Prepare messages (same as execute)
        conversation_messages = []

        if self.system_prompt:
            conversation_messages.append(
                ChatMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            )

        if self.conversation_history:
            recent_history = self.conversation_history[-self.max_history :]
            conversation_messages.extend(recent_history)

        conversation_messages.extend(messages)

        try:
            # Get streaming LLM client
            streaming_llm_client = get_langgraph_llm_service(
                llm_config_id=self.llm_config_id,
                temperature=temp,
                max_tokens=max_tokens,
            )
            
            # Use LangChain streaming
            accumulated_content = ""
            async for chunk in streaming_llm_client.astream(conversation_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    accumulated_content += chunk.content
                    
                    yield ChatCompletionChunk(
                        id=completion_id,
                        object="chat.completion.chunk",
                        created=int(start_time),
                        model=self.id,
                        choices=[
                            {
                                "index": 0,
                                "delta": {"content": chunk.content},
                                "finish_reason": None,
                            },
                        ],
                    )

            # Final chunk with finish reason
            yield ChatCompletionChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=self.id,
                choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
            )

            # Update conversation history
            self.conversation_history.extend(messages)
            self.conversation_history.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=accumulated_content),
            )

        except Exception as e:
            # Yield error chunk
            yield ChatCompletionChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=self.id,
                choices=[{"index": 0, "delta": {}, "finish_reason": "error"}],
                error=str(e),
            )

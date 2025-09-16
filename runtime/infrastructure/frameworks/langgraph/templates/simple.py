"""Simple Test Agent Template - No external dependencies."""

import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, UTC
from typing import Any, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from runtime.domain.services.llm.llm_service import LLMService
from runtime.domain.services.toolset.toolset_service import ToolsetService
from runtime.infrastructure.web.models.responses import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessageResponse,
)
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.templates.base import BaseAgentTemplate
from .base import BaseLangGraphAgent


class SimpleTestAgentConfig(BaseModel):
    """Configuration for Simple Test Agent."""

    response_prefix: str = Field(
        default="Test: ", description="Prefix for test responses", min_length=1, max_length=50
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.", description="System prompt for the agent"
    )


class SimpleTestAgent(BaseAgentTemplate, BaseLangGraphAgent):
    """Simple test agent template for validation - no external dependencies."""

    # Template metadata (class variables)
    template_name: str = "Simple Test Agent"
    template_id: str = "langgraph-simple-test"
    template_version: str = "1.0.0"
    template_description: str = "Simple test agent for system validation"
    framework: str = "langgraph"

    # Configuration schema (class variables)
    config_schema: type[BaseModel] = SimpleTestAgentConfig

    def __init__(
        self, 
        configuration: AgentConfiguration, 
        llm_service: LLMService, 
        toolset_service: Optional[ToolsetService] = None,
        metadata: Optional[dict[str, Any]] = None, 
    ):
        """Initialize the simple test agent."""
        super().__init__(configuration, llm_service, toolset_service, metadata)
        self._graph: CompiledStateGraph | None = None
        
        # Extract template-specific configuration using helper methods
        self.response_prefix = self.get_config_value("response_prefix", "Test: ")
        
        # Use system_prompt from base class initialization (already extracted from config)
        # Fallback to template default if not provided
        if not self.system_prompt:
            self.system_prompt = "You are a helpful assistant."

    def _convert_to_langgraph_messages(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert our ChatMessage format to LangGraph's BaseMessage format."""
        langgraph_messages = []
        
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                langgraph_messages.append(SystemMessage(content=message.content))
            elif message.role == MessageRole.USER:
                langgraph_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langgraph_messages.append(AIMessage(content=message.content))
            else:
                # Default to human message for unknown roles
                langgraph_messages.append(HumanMessage(content=message.content))
        
        return langgraph_messages

    def _convert_from_langgraph_message(self, message: BaseMessage) -> ChatMessage:
        """Convert LangGraph's BaseMessage format to our ChatMessage format."""
        if isinstance(message, SystemMessage):
            role = MessageRole.SYSTEM
        elif isinstance(message, HumanMessage):
            role = MessageRole.USER
        elif isinstance(message, AIMessage):
            role = MessageRole.ASSISTANT
        else:
            # Default to assistant for unknown message types
            role = MessageRole.ASSISTANT
        
        # Handle both string content and list content
        content = message.content
        if isinstance(content, list):
            # Extract text from content list
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        text_parts.append(item["text"])
                    elif "content" in item:
                        text_parts.append(item["content"])
                else:
                    text_parts.append(str(item))
            content = "".join(text_parts)
        
        return ChatMessage(
            role=role,
            content=content
        )

    async def _build_graph(self):
        """Build the execution graph for simple test agent."""
        # Simple test agent doesn't need a complex graph
        # Return None for simplicity
        toolset_client = await self.get_toolset_client()
        if toolset_client is None:
            tools = []
        else:
            tools = await toolset_client.get_tools()
        
        # Use parameter-aware client to ensure the LLM is configured with 
        # the agent's default temperature and max_tokens
        llm_client = await self.get_llm_client(
            temperature=self.default_temperature,
            max_tokens=self.default_max_tokens
        )
        
        return create_react_agent(
            model=llm_client,  # type: ignore - LLMClient is actually a BaseChatModel at runtime
            tools=tools,
            prompt=self.system_prompt
        )

    async def execute(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse:
        """Execute the simple test agent using LangGraph."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        # Get effective execution parameters using base class helpers
        # Note: For this LangGraph template using create_react_agent, 
        # temperature and max_tokens are configured at the LLM client level
        # rather than passed per execution. This demonstrates the pattern
        # for templates that do support per-execution parameters.
        _effective_temperature = self.get_effective_temperature(temperature)
        _effective_max_tokens = self.get_effective_max_tokens(max_tokens)
        
        try:
            # Get the compiled graph
            graph = await self.graph
            
            # Convert our messages to LangGraph format
            langgraph_messages = self._convert_to_langgraph_messages(messages)
            
            # Prepare the input state for LangGraph
            input_state = {
                "messages": langgraph_messages,
            }
            
            # Execute the graph
            result = await graph.ainvoke(input_state)
            
            # Extract the final response from the graph result
            final_messages = result.get("messages", [])
            if not final_messages:
                raise RuntimeError("No messages returned from LangGraph execution")
            
            # Get the last message (should be the assistant's response)
            last_message = final_messages[-1]
            
            # Convert back to our format
            response_message = self._convert_from_langgraph_message(last_message)
            
            # Add response prefix if configured (create new message since ChatMessage is frozen)
            if self.response_prefix and not response_message.content.startswith(self.response_prefix):
                response_message = ChatMessage(
                    role=response_message.role,
                    content=self.response_prefix + response_message.content,
                    timestamp=response_message.timestamp,
                    metadata=response_message.metadata
                )
            
            # Convert domain ChatMessage to response model ChatMessageResponse
            response_model = ChatMessageResponse(
                role=response_message.role,
                content=response_message.content,
                timestamp=response_message.timestamp,
                metadata=response_message.metadata
            )
            
            # Create response
            return ChatCompletionResponse(
                id=completion_id,
                object="chat.completion",
                created=int(start_time),
                model=self.id,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=response_model,
                        finish_reason="stop",
                    ),
                ],
                usage=ChatCompletionUsage(
                    prompt_tokens=result.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=result.get("usage", {}).get("completion_tokens", 0),
                    total_tokens=result.get("usage", {}).get("total_tokens", 0),
                ),
                metadata=metadata,  # Pass through the metadata parameter
            )
            
        except Exception as e:
            raise RuntimeError(f"Simple test agent execution failed: {e}")

    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream the simple test agent execution using LangGraph."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        # Get effective execution parameters using base class helpers
        # Note: Similar to execute(), these parameters would be used in templates
        # that support per-execution parameter configuration
        _effective_temperature = self.get_effective_temperature(temperature)
        _effective_max_tokens = self.get_effective_max_tokens(max_tokens)
        
        try:
            # Get the compiled graph
            graph = await self.graph
            
            # Convert our messages to LangGraph format
            langgraph_messages = self._convert_to_langgraph_messages(messages)
            
            # Prepare the input state for LangGraph
            input_state = {
                "messages": langgraph_messages,
            }
            
            # Stream the graph execution
            accumulated_content = ""
            prefix_added = False
            
            async for chunk in graph.astream(input_state):
                # Process each chunk from LangGraph
                if isinstance(chunk, dict):
                    # Look for message updates in the chunk
                    messages_update = chunk.get("messages", [])
                    
                    if messages_update:
                        # Get the latest message
                        latest_message = messages_update[-1]
                        
                        if hasattr(latest_message, 'content'):
                            current_content = latest_message.content
                        else:
                            current_content = str(latest_message)
                        
                        # Add prefix to the first chunk if needed
                        if not prefix_added and self.response_prefix:
                            current_content = self.response_prefix + current_content
                            prefix_added = True
                        
                        # Calculate the new content to yield
                        if len(current_content) > len(accumulated_content):
                            new_content = current_content[len(accumulated_content):]
                            accumulated_content = current_content
                            
                            # Yield the new content as a chunk
                            yield ChatCompletionChunk(
                                id=completion_id,
                                object="chat.completion.chunk",
                                created=int(start_time),
                                model=self.id,
                                system_fingerprint="fp_simple",  # Required field
                                choices=[
                                    ChatCompletionChunkChoice(
                                        index=0,
                                        delta=ChatMessageResponse(
                                            role=MessageRole.ASSISTANT,
                                            content=new_content,
                                            timestamp=datetime.now(UTC),
                                            metadata={}
                                        ),
                                        finish_reason=None,
                                    ),
                                ],
                            )
            
            # Final chunk with finish reason
            yield ChatCompletionChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=self.id,
                system_fingerprint="fp_simple",  # Required field
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChatMessageResponse(
                            role=MessageRole.ASSISTANT,
                            content="",
                            timestamp=datetime.now(UTC),
                            metadata={}
                        ),
                        finish_reason="stop",
                    ),
                ],
            )
            
        except Exception:
            # Yield error chunk
            yield ChatCompletionChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=self.id,
                system_fingerprint="fp_simple",  # Required field
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChatMessageResponse(
                            role=MessageRole.ASSISTANT,
                            content="",
                            timestamp=datetime.now(UTC),
                            metadata={}
                        ),
                        finish_reason="error",
                    ),
                ],
            )

    

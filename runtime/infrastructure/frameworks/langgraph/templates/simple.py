"""Simple Test Agent Template - No external dependencies."""

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from runtime.infrastructure.web.models.requests import CreateAgentRequest
from runtime.infrastructure.web.models.responses import (
    ChatChoice,
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatUsage,
)
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from .base import BaseLangGraphAgent


class SimpleTestAgentConfig(BaseModel):
    """Configuration for Simple Test Agent."""

    response_prefix: str = Field(
        default="Test: ", description="Prefix for test responses", min_length=1, max_length=50
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.", description="System prompt for the agent"
    )


class SimpleTestAgent(BaseLangGraphAgent):
    """Simple test agent template for validation - no external dependencies."""

    # Template metadata (class variables)
    template_name: str = "Simple Test Agent"
    template_id: str = "simple-test"
    template_version: str = "1.0.0"
    template_description: str = "Simple test agent for system validation"
    framework: str = "test"

    # Configuration schema (class variables)
    config_schema: type[BaseModel] = SimpleTestAgentConfig

    def __init__(self, agent_data: CreateAgentRequest, llm_service=None, toolset_service=None):
        """Initialize the simple test agent."""
        super().__init__(agent_data, llm_service, toolset_service)

        # Extract configuration using structured access
        config = agent_data.get_agent_configuration()
        self.response_prefix = self.template_config.get("response_prefix", "Test: ")
        # Use system_prompt from structured config if available, fallback to template config
        self.system_prompt = config.system_prompt or self.template_config.get("system_prompt", "You are a helpful assistant.")

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
        
        return ChatMessage(
            role=role,
            content=message.content
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
        
        return create_react_agent(
            model=await self.get_llm_client(),
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
            
            # Add response prefix if configured
            if self.response_prefix and not response_message.content.startswith(self.response_prefix):
                response_message.content = self.response_prefix + response_message.content
            
            # Create response
            return ChatCompletionResponse(
                id=completion_id,
                object="chat.completion",
                created=int(start_time),
                model=self.id,
                choices=[
                    ChatChoice(
                        index=0,
                        message=response_message,
                        finish_reason="stop",
                    ),
                ],
                usage=ChatUsage(
                    prompt_tokens=result.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=result.get("usage", {}).get("completion_tokens", 0),
                    total_tokens=result.get("usage", {}).get("total_tokens", 0),
                ),
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
                                choices=[
                                    {
                                        "index": 0,
                                        "delta": {"content": new_content},
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
                choices=[
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    },
                ],
            )
            
        except Exception as e:
            # Yield error chunk
            yield ChatCompletionChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=self.id,
                choices=[
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "error",
                    },
                ],
                error=str(e),
            )

    

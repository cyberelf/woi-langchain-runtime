"""LangGraph Base Agent Template - Framework-specific base class."""

import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional, TypeVar
from datetime import datetime, UTC

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph

from runtime.infrastructure.web.models.responses import (
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessageResponse,
    StreamingChunk,
    StreamingChunkChoice,
    StreamingChunkDelta,
)
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.templates.base import BaseAgentTemplate
from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
from runtime.domain.value_objects.agent_configuration import AgentConfiguration

# Type variable for state management
StateType = TypeVar('StateType')


class BaseLangGraphAgent(BaseAgentTemplate, ABC):
    """
    Base class for LangGraph agent templates.

    Provides common functionality for LangGraph-based agents including:
    - Message conversion utilities
    - State creation interface
    - Common execution patterns
    - LLM client integration
    """

    def __init__(
                    self, 
                    configuration: AgentConfiguration, 
                    llm_service: LangGraphLLMService, 
                    toolset_service: Optional[LangGraphToolsetService] = None, 
                    metadata: Optional[dict[str, Any]] = None
                ):
        super().__init__(configuration, metadata)

        self.llm_service = llm_service
        self.toolset_service = toolset_service

        self.llm_config_id = configuration.llm_config_id
        self.default_temperature = configuration.get_temperature()
        self.default_max_tokens = configuration.get_max_tokens()
        self.toolset_configs = configuration.get_toolset_names()

        self.llm_client = self._get_llm_client()
        self.toolset_client = self._get_toolset_client()

    def _get_llm_client(self, temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        """Get LLM client configured with execution parameters."""
        execution_params = {}
        
        # Use effective parameters (template defaults vs execution overrides)
        effective_temperature = temperature if temperature is not None else self.default_temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if effective_temperature is not None:
            execution_params["temperature"] = effective_temperature
        if effective_max_tokens is not None:
            execution_params["max_tokens"] = effective_max_tokens
            
        return self.llm_service.get_client(self.llm_config_id, **execution_params)

    def _get_toolset_client(self):
        """Get toolset client for this agent."""
        if self.toolset_service and self.toolset_configs:
            return self.toolset_service.create_client(self.toolset_configs)
        return None

    @abstractmethod
    async def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph execution graph. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _create_initial_state(self, messages: list[ChatMessage]) -> Any:
        """Create the initial state for LangGraph execution.
        
        Each template defines its own state structure.
        Args:
            messages: Input messages to convert to the template's state format
        Returns:
            State object appropriate for this template's graph
        """
        pass

    @abstractmethod
    async def _extract_final_content(self, final_state: Any) -> str:
        """Extract the final response content from the execution state.
        
        Args:
            final_state: The final state returned by LangGraph execution
        Returns:
            The response content as a string
        """
        pass

    @abstractmethod
    async def _process_stream_chunk(
        self, 
        chunk: Any, 
        completion_id: str, 
        start_time: float
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Process a streaming chunk from LangGraph execution.
        
        Args:
            chunk: Raw chunk from LangGraph streaming
            completion_id: Unique completion ID for this execution
            start_time: Start time of the execution
        Yields:
            StreamingChunk objects for intermediate streaming responses
        """
        pass

    @property
    async def graph(self) -> CompiledStateGraph:
        """Get the LangGraph execution graph."""
        if not hasattr(self, '_graph') or self._graph is None:
            self._graph = await self._build_graph()
        return self._graph

    def _convert_to_langgraph_messages(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert ChatMessage format to LangGraph BaseMessage format."""
        langgraph_messages = []
        
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                langgraph_messages.append(SystemMessage(content=message.content))
            elif message.role == MessageRole.USER:
                langgraph_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langgraph_messages.append(AIMessage(content=message.content))
            else:
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
            content=content,
            timestamp=datetime.now(UTC),
            metadata={}
        )


    def _create_chat_message_response(
        self, content: str, metadata: Optional[dict[str, Any]] = None
    ) -> ChatMessageResponse:
        """Create a standardized ChatMessageResponse."""
        return ChatMessageResponse(
            role=MessageRole.ASSISTANT,
            content=content,
            timestamp=datetime.now(UTC),
            metadata=metadata or {}
        )


    def _get_system_fingerprint(self) -> str:
        """Get system fingerprint for this agent type."""
        return f"fp_{getattr(self, 'template_id', 'agent')}"

    async def execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """Standard execute implementation for LangGraph agents."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        try:
            # Get the compiled graph
            graph = await self.graph
            
            # Create the initial state using template-specific method
            initial_state = self._create_initial_state(messages)
            
            # Execute the graph
            final_state = await graph.ainvoke(initial_state)
            
            # Extract content using template-specific method
            content = await self._extract_final_content(final_state)
            
            # Create response message
            response_message = self._create_chat_message_response(content, metadata)
            
            return ChatCompletionResponse(
                id=completion_id,
                object="chat.completion",
                created=int(start_time),
                model=getattr(self, 'id', 'unknown'),
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=response_message,
                        finish_reason="stop",
                    ),
                ],
                usage=ChatCompletionUsage(
                    prompt_tokens=0,  # Simplified for now
                    completion_tokens=0,
                    total_tokens=0,
                ),
                metadata=metadata,
            )
            
        except Exception as e:
            raise RuntimeError(f"Agent execution failed: {e}")

    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Standard stream execute implementation for LangGraph agents."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        try:
            # Get the compiled graph
            graph = await self.graph
            
            # Create the initial state using template-specific method
            initial_state = self._create_initial_state(messages)
            
            # Stream the graph execution
            async for chunk in graph.astream(initial_state, stream_mode="values"):
                # Let subclasses handle chunk processing for streaming
                # This is template-specific since state structures differ
                chunk_generator = self._process_stream_chunk(chunk, completion_id, start_time)
                async for completion_chunk in chunk_generator:
                    yield completion_chunk
            
            # Final chunk with finish reason
            yield StreamingChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=getattr(self, 'id', 'unknown'),
                system_fingerprint=self._get_system_fingerprint(),
                choices=[
                    StreamingChunkChoice(
                        index=0,
                        delta=StreamingChunkDelta(content=""),
                        finish_reason="stop",
                    ),
                ],
            )
            
        except Exception as e:
            # Yield error chunk
            yield StreamingChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(start_time),
                model=getattr(self, 'id', 'unknown'),
                system_fingerprint=self._get_system_fingerprint(),
                choices=[
                    StreamingChunkChoice(
                        index=0,
                        delta=StreamingChunkDelta(content=f"Error: {e}"),
                        finish_reason="error",
                    ),
                ],
            )

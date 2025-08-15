"""Base Agent Template - Enhanced Agent with Template Metadata."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from runtime.infrastructure.web.models.requests import CreateAgentRequest
from runtime.infrastructure.web.models.responses import (
    ChatCompletionChunk,
    ChatCompletionResponse,
)
from runtime.domain.value_objects.chat_message import ChatMessage
from runtime.templates.base import BaseAgentTemplate


class BaseLangGraphAgent(BaseAgentTemplate, ABC):
    """
    Base class for agent templates.

    Agent classes ARE templates - they contain both template metadata
    (as class variables) and execution logic (as instance methods).
    """

    # Template Metadata (class variables)
    template_name: str = "LangGraph Base Agent"
    template_id: str = "langgraph-base-agent"
    template_version: str = "1.0.0"
    template_description: str = "LangGraph base agent template"

    # Configuration Schema (class variable)
    config_schema: type[BaseModel] = BaseModel

    def __init__(self, agent_data: CreateAgentRequest, llm_service=None, toolset_service=None) -> None:
        """Initialize agent instance with configuration."""
        super().__init__(agent_data, llm_service, toolset_service)
    
        self._graph: CompiledStateGraph | None = None

    @abstractmethod
    async def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph execution graph. Must be implemented by subclasses."""
        pass

    @property
    async def graph(self) -> CompiledStateGraph:
        """Get the LangGraph execution graph."""
        if self._graph is None:
            self._graph = await self._build_graph()
        return self._graph

    @abstractmethod
    async def execute(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse:
        """Execute the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream the agent. Must be implemented by subclasses."""
        pass
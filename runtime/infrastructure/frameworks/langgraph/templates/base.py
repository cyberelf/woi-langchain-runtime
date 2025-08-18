"""Base Agent Template - Enhanced Agent with Template Metadata."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from runtime.infrastructure.web.models.responses import (
    ChatCompletionChunk,
    ChatCompletionResponse,
)
from runtime.domain.value_objects.chat_message import ChatMessage


class BaseLangGraphAgent(ABC):
    """
    Base class for agent templates.

    Agent classes ARE templates - they contain both template metadata
    (as class variables) and execution logic (as instance methods).
    """

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

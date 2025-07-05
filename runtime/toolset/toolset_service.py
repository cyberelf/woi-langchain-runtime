"""Toolset Service - Manages toolsets and their integration with MCP proxy and LangChain.

This module provides comprehensive toolset management including:
- Toolset resolution from agentdata to MCP proxy configurations
- LangChain MCP adapter client creation and management
- Tool bridging between MCP services and LangChain agents
- Framework-agnostic toolset handling
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolsetType(str, Enum):
    """Type of toolset."""

    MCP = "mcp"
    CUSTOM = "custom"

class ToolsetConfiguration(BaseModel):
    """Configuration for a toolset from MCP proxy."""

    name: str
    description: str
    version: str
    toolset_type: ToolsetType
    config: dict[str, Any]
    metadata: dict[str, Any]


class ToolsetClient(Protocol):
    """Protocol for toolset clients that bridge toolsets and tools to agents."""

    async def get_toolsets(self) -> dict[str, str]:
        """Get the toolsets descriptions provided by this client."""
        ...

    async def get_tools(self) -> list[Any]:
        """Get the tools provided by this client."""
        ...

    async def get_tool_by_name(self, tool_name: str) -> Any:
        """Get a tool by name."""
        ...

    async def get_tools_by_toolset(self, toolset_name: str) -> list[Any]:
        """Get the tools provided by a toolset."""
        ...


class ToolsetResolverInterface(ABC):
    """Interface for toolset resolvers."""

    @abstractmethod
    async def resolve_toolsets(self, toolset_names: list[str]) -> list[ToolsetConfiguration]:
        """Resolve a list of toolset names to their configurations."""
        pass

    @abstractmethod
    async def list_available_toolsets(self) -> list[ToolsetConfiguration]:
        """List all available toolsets."""
        pass


class ToolsetClientFactoryInterface(ABC):
    """Interface for toolset client factories."""

    @abstractmethod
    async def create_client(self, config: list[ToolsetConfiguration]) -> ToolsetClient:
        """Create a toolset client from configuration."""
        pass


class ToolsetService:
    """
    Main toolset service that manages toolsets.

    This service provides:
    - Toolset resolution from names to configurations
    - Toolset client creation and management
    """

    def __init__(self, resolver: ToolsetResolverInterface, client_factory: ToolsetClientFactoryInterface):
        self.resolver = resolver
        self.client_factory = client_factory


    async def get_toolset_client(self, toolset_names: list[str]) -> ToolsetClient:
        """Get the toolset client."""
        logger.info(f"Resolving {len(toolset_names)} toolsets")

        toolset_configs = await self.resolver.resolve_toolsets(toolset_names)

        client = await self.client_factory.create_client(toolset_configs)
        return client


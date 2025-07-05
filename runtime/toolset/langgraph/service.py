"""
Toolset client for LangGraph.
"""

import logging
import os
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from runtime.toolset.toolset_service import (ToolsetClient,
                                             ToolsetClientFactoryInterface,
                                             ToolsetConfiguration,
                                             ToolsetResolverInterface,
                                             ToolsetService, ToolsetType)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for custom tools."""

    def __init__(self):
        self.toolsets = {}

    def register_tool(self, tool: Any, toolset_name: str = "custom"):
        """Register a tool."""
        if toolset_name not in self.toolsets:
            self.toolsets[toolset_name] = []
        self.toolsets[toolset_name].append(tool)

    def get_tools(self, category: str = "custom") -> list[Any]:
        """Get the tools for a given category."""
        return self.toolsets[category]
    
    def get_toolsets(self) -> list[str]:
        """Get the toolsets."""
        return self.toolsets.keys()
    
    def get_toolset_config(self, toolset_name: str) -> ToolsetConfiguration:
        """Get a toolset by name."""
        if toolset_name not in self.toolsets:
            raise ValueError(f"Toolset {toolset_name} not found in registry")
        
        return ToolsetConfiguration(
            name=toolset_name,
            description=f"Custom toolset with tools: {', '.join([tool.name for tool in self.toolsets[toolset_name]])}",
            version="1.0.0",
            toolset_type=ToolsetType.CUSTOM,
            config={},
            metadata={},
        )

    def get_all_toolset_configs(self) -> list[ToolsetConfiguration]:
        """Get all toolset configurations."""
        return [self.get_toolset_config(toolset_name) for toolset_name in self.get_toolsets()]
    
tool_registry = ToolRegistry()


class MCPToolsetClient(ToolsetClient):
    """Toolset client for MCP."""

    def __init__(self, configs: list[ToolsetConfiguration]):
        self.configs = configs
        self.mcp_config = self._validate_config(configs)
        self._mcp_client = self._create_mcp_client()

    def _get_mcp_config(self, configs: list[ToolsetConfiguration]) -> dict[str, Any]:
        """Validate the toolset configuration."""
        mcp_config = {}
        for config in configs:
            if config.toolset_type != ToolsetType.MCP:
                raise ValueError(f"Toolset type must be MCP: {config.toolset_type}")
            mcp_config[config.name] = config.config
        return mcp_config

    def _create_mcp_client(self) -> MultiServerMCPClient:
        """Create an MCP client."""
        return MultiServerMCPClient(self.configs[0].config)

    async def get_toolsets(self) -> dict[str, str]:
        """Get the toolsets descriptions provided by this client."""
        return {config.name: config.description for config in self.configs}

    async def get_tools(self) -> list[Any]:
        """Get the tools provided by this client."""
        return await self._mcp_client.get_tools()

    async def get_tool_by_name(self, tool_name: str) -> Any:
        """Get a tool by name."""
        tools = await self._mcp_client.get_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool
        raise ValueError(f"Tool {tool_name} not found")

    async def get_tools_by_toolset(self, toolset_name: str) -> list[Any]:
        """Get the tools provided by a toolset."""
        return await self._mcp_client.get_tools(server_name=toolset_name)


class CustomToolsetClient(ToolsetClient):
    """Toolset client for local tools."""

    def __init__(self, configs: list[ToolsetConfiguration]):
        self.configs = configs
        self._toolsets = self._get_toolsets_from_registry()

    def _get_toolsets_from_registry(self) -> list[str]:
        """Get the toolsets from the registry.
        
        The toolsets are returned as a dictionary with the toolset name as the key and the tools as the value.
        The tools are returned as a list of tool objects.
        The tool objects are returned as a list of tool objects.
        The tool objects are returned as a list of tool objects.
        """
        toolsets = {}
        for config in self.configs:
            if config.toolset_type == ToolsetType.CUSTOM:
                if config.name not in tool_registry.get_toolsets():
                    raise ValueError(f"Toolset {config.name} not found in registry")
                toolsets[config.name] = tool_registry.get_tools(config.name)
            else:
                raise ValueError(f"Toolset type must be CUSTOM: {config.toolset_type}")
        return toolsets

    async def get_toolsets(self) -> dict[str, str]:
        """Get the toolsets descriptions provided by this client."""
        return {config.name: config.description for config in self.configs}
    
    async def get_tools(self) -> list[Any]:
        """Get the tools provided by this client."""
        return [tool for toolset in self._toolsets.values() for tool in toolset]
    
    async def get_tool_by_name(self, tool_name: str) -> Any:
        """Get a tool by name."""
        for toolset in self._toolsets.values():
            for tool in toolset:
                if tool.name == tool_name:
                    return tool
        raise ValueError(f"Tool {tool_name} not found")
    
    async def get_tools_by_toolset(self, toolset_name: str) -> list[Any]:
        """Get the tools provided by a toolset."""
        if toolset_name in self._toolsets:
            return self._toolsets[toolset_name]
        raise ValueError(f"Toolset {toolset_name} not found")
    
class CompositeToolsetClient(ToolsetClient):
    """Composite toolset client."""
    
    def __init__(self, clients: list[ToolsetClient]):
        self.clients = clients
        
    async def get_toolsets(self) -> dict[str, str]:
        """Get the toolsets descriptions provided by this client."""
        return {config.name: config.description for config in self.configs}
    
    async def get_tools(self) -> list[Any]:
        """Get the tools provided by this client."""
        return [tool for client in self.clients for tool in client.get_tools()]
    
    async def get_tool_by_name(self, tool_name: str) -> Any:
        """Get a tool by name."""
        for client in self.clients:
            try:
                return await client.get_tool_by_name(tool_name)
            except ValueError:
                continue
        raise ValueError(f"Tool {tool_name} not found")
    
    async def get_tools_by_toolset(self, toolset_name: str) -> list[Any]:
        """Get the tools provided by a toolset."""
        for client in self.clients:
            try:
                return await client.get_tools_by_toolset(toolset_name)
            except ValueError:
                continue
        raise ValueError(f"Toolset {toolset_name} not found")
    

class ToolsetClientFactory(ToolsetClientFactoryInterface):
    """Factory for toolset clients."""

    async def create_client(self, config: list[ToolsetConfiguration], ) -> ToolsetClient:
        """Create a toolset client from configuration."""
        # separate the configs by toolset type
        mcp_configs = [config for config in config if config.toolset_type == ToolsetType.MCP]
        custom_configs = [config for config in config if config.toolset_type == ToolsetType.CUSTOM]
        if len(mcp_configs) > 0 and len(custom_configs) > 0:
            return CompositeToolsetClient([MCPToolsetClient(mcp_configs), CustomToolsetClient(custom_configs)])
        elif len(mcp_configs) > 0:
            return MCPToolsetClient(mcp_configs)
        elif len(custom_configs) > 0:
            return CustomToolsetClient(custom_configs)
        else:
            raise ValueError("No toolset configurations provided")

class ToolsetResolver(ToolsetResolverInterface):
    """Resolver for toolsets."""

    def __init__(self, toolset_registry: ToolRegistry):
        self.toolset_registry = toolset_registry

    async def resolve_toolsets(self, toolset_names: list[str]) -> list[ToolsetConfiguration]:
        """Resolve a list of toolset names to their configurations."""
        toolset_configs = []
        for toolset_name in toolset_names:
            toolset_configs.append(self.toolset_registry.get_toolset(toolset_name))
        return toolset_configs
    
    async def list_available_toolsets(self) -> list[str]:
        """List all available toolsets."""
        return self.toolset_registry.get_all_toolset_configs()


def get_toolset_service() -> ToolsetService:
    """Get a toolset service from configuration."""
    resolver = ToolsetResolver(tool_registry)
    client_factory = ToolsetClientFactory()

    return ToolsetService(resolver, client_factory)

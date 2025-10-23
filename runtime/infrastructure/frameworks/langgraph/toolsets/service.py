"""LangGraph toolset service implementation.

This module provides toolset services specifically designed for LangGraph agents.
"""

import logging
from typing import Any, Optional, override

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlalchemy import over

from runtime.core.interfaces import ToolsetServiceInterface
from ..config import ToolsetsConfig, MCPToolsetConfig

logger = logging.getLogger(__name__)


class LangGraphToolsetService(ToolsetServiceInterface):
    """Toolset service for LangGraph framework."""
    
    def __init__(self, toolsets_config: Optional[ToolsetsConfig]=None):
        """Initialize with toolset configurations.
        
        Args:
            toolsets_config: ToolsetsConfig pydantic model or dict (for backward compatibility)
        """
        
        self.clients = {}
        
        if toolsets_config is None:
            # Create default configuration
            self._toolsets_config = ToolsetsConfig(mcp={}, custom="all")
        else:   
            # Use pydantic config directly
            self._toolsets_config = toolsets_config

        logger.info(
            f"LangGraphToolsetService initialized with {len(self._toolsets_config.mcp)} "
            f"MCP toolsets and custom tools: {self._toolsets_config.custom}"
        )
    
    def create_client(self, toolset_names: list[str]) -> "LangGraphToolsetClient":
        """Create a toolset client for LangGraph."""
        return LangGraphToolsetClient(self._toolsets_config, toolset_names)
    
    @override
    def get_all_toolset_names(self) -> list[str]:
        """Get all available toolset names."""
        names = list(self._toolsets_config.mcp.keys())
        
        # Add "custom" if custom tools are configured
        if self._toolsets_config.custom:
            names.append("custom")
        
        return names

    @override
    async def shutdown(self) -> None:
        """Shutdown the toolset service."""
        pass

class LangGraphToolsetClient:
    """Toolset client for LangGraph agents."""
    
    def __init__(self, toolsets_config: ToolsetsConfig, toolset_names: list[str]):
        """Initialize with toolsets config and requested toolset names."""
        self.toolsets_config = toolsets_config
        self.toolset_names = toolset_names
        self._tools = None

    @property
    async def tools(self) -> list[BaseTool]:
        """Get LangGraph-compatible tools."""
        if self._tools is None:
            self._tools = await self._get_tools()
        
        return self._tools

    async def _get_tools(self) -> list[BaseTool]:
        """Get LangGraph-compatible tools."""
        if self._tools is None:
            self._tools = []
            
            for name in self.toolset_names:
                # Check if it's an MCP toolset
                if name in self.toolsets_config.mcp:
                    mcp_config = self.toolsets_config.mcp[name]
                    mcp_tools = await self._get_mcp_tools(name, mcp_config)
                    self._tools.extend(mcp_tools)
                    logger.debug(f"Loaded MCP tools from toolset '{name}'")
                # Check if it's a special "custom" keyword for custom tools
                elif name == "custom":
                    custom_tools = await self._get_custom_tools()
                    self._tools.extend(custom_tools)
                    logger.debug(f"Loaded custom tools")
                else:
                    logger.warning(f"No configuration found for toolset '{name}', skipping")
        
        return self._tools
    
    async def _get_mcp_tools(self, name: str, config: MCPToolsetConfig) -> list[BaseTool]:
        """Get tools from MCP toolset."""
        try:
            # Build connections dict following LangChain MCP spec
            connections: dict[str, Any] = {}
            for server in config.servers:
                # Create appropriate connection dict based on transport type
                if server.transport == "stdio":
                    assert server.command is not None, "Command required for stdio transport"
                    connection = {
                        "transport": "stdio",
                        "command": server.command,
                        "args": server.args,
                        "env": server.env
                    }
                elif server.transport == "streamable_http":
                    assert server.url is not None, "URL required for streamable_http transport"
                    connection = {
                        "transport": "streamable_http",
                        "url": server.url,
                        "headers": server.env  # Pass env vars as headers
                    }
                elif server.transport == "sse":
                    assert server.url is not None, "URL required for SSE transport"
                    connection = {
                        "transport": "sse",
                        "url": server.url,
                        "headers": server.env  # Pass env vars as headers
                    }
                else:
                    logger.warning(f"Unknown transport type: {server.transport}")
                    continue
                
                connections[server.name] = connection
            
            if not connections:
                logger.warning(f"No valid MCP connections configured for {name}")
                return []
            
            client = MultiServerMCPClient(connections)
            return await client.get_tools()
        except Exception as e:
            logger.warning(f"Failed to get MCP tools from {name}: {e}")
            return []
    
    async def _get_custom_tools(self) -> list[BaseTool]:
        """Get tools from custom toolset configuration."""
        logger.info(f"Loading custom tools")
        
        custom_config = self.toolsets_config.custom
        
        # Check if it's "all" - load all plugin tools
        if custom_config == "all":
            return await self._get_all_plugin_tools()
        
        # Otherwise, it's a list of specific tool names
        if isinstance(custom_config, list):
            return await self._resolve_tool_list(custom_config)
        
        return []
    
    async def _resolve_tool_list(self, tool_names: list[str]) -> list[BaseTool]:
        """Resolve tools from explicit tool name list (plugins only).
        
        Args:
            tool_names: List of tool names to load
            
        Returns:
            List of instantiated tool objects
        """
        from runtime.settings import settings
        
        tools = []
        
        for tool_name in tool_names:
            tool_instance = None
            
            # Try plugin registry
            if settings.enable_plugin_discovery:
                try:
                    from runtime.core.plugin import get_plugin_registry
                    registry = get_plugin_registry()
                    plugin_meta = registry.get_tool(tool_name)
                    
                    if plugin_meta:
                        try:
                            tool_instance = plugin_meta.class_obj()
                            logger.debug(f"Loaded plugin tool: {tool_name}")
                        except Exception as e:
                            logger.error(f"Failed to instantiate plugin tool '{tool_name}': {e}")
                except ImportError:
                    logger.error("Plugin system not available")
            else:
                logger.warning("Plugin discovery disabled, cannot load tools")
            
            if tool_instance:
                tools.append(tool_instance)
            else:
                logger.warning(f"Tool '{tool_name}' not found in plugin registry")
        
        logger.info(f"Resolved {len(tools)}/{len(tool_names)} tools from plugin registry")
        return tools
    
    async def _get_all_plugin_tools(self) -> list[BaseTool]:
        """Get all available plugin tools via auto-discovery.
        
        Returns:
            List of all registered plugin tool instances
        """
        from runtime.settings import settings
        
        if not settings.enable_plugin_discovery:
            logger.warning("Plugin discovery disabled, no plugin tools available")
            return []
        
        try:
            from runtime.core.plugin import get_plugin_registry
            registry = get_plugin_registry()
            
            tools = []
            for tool_metadata in registry.list_tools():
                try:
                    tool_instance = tool_metadata.class_obj()
                    tools.append(tool_instance)
                    logger.debug(f"Auto-discovered plugin tool: {tool_metadata.plugin_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to instantiate plugin tool '{tool_metadata.plugin_id}': {e}"
                    )
            
            logger.info(f"Auto-discovered {len(tools)} plugin tools")
            return tools
            
        except ImportError:
            logger.warning("Plugin system not available")
            return []

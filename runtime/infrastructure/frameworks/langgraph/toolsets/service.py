"""LangGraph toolset service implementation.

This module provides toolset services specifically designed for LangGraph agents.
"""

import logging
from typing import Any, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

# Removed domain abstraction - using concrete implementation

from ..config import ToolsetsConfig, ToolsetConfig

logger = logging.getLogger(__name__)


class LangGraphToolsetService:
    """Toolset service for LangGraph framework."""
    
    def __init__(self, toolsets_config: Optional[ToolsetsConfig]=None):
        """Initialize with toolset configurations.
        
        Args:
            toolsets_config: ToolsetsConfig pydantic model or dict (for backward compatibility)
        """
        
        self.clients = {}
        
        if toolsets_config is None:
            # Create default configuration
            self._toolsets_config = ToolsetsConfig()
        else:   
            # Use pydantic config directly
            self._toolsets_config = toolsets_config

        logger.info(
            f"LangGraphToolsetService initialized with {len(self._toolsets_config.toolsets)} "
            f"toolset configurations"
        )
    
    def create_client(self, toolset_names: list[str]) -> "LangGraphToolsetClient":
        """Create a toolset client for LangGraph."""
        return LangGraphToolsetClient(self._toolsets_config, toolset_names)

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
        tools = []
        if self._tools is None:
            self._tools = []
            for name in self.toolset_names:
                if name in self.toolsets_config.toolsets:
                    config = self.toolsets_config.toolsets[name]
                    if config.type == "mcp":
                        # Handle MCP toolsets
                        mcp_tools = await self._get_mcp_tools(name, config)
                        self._tools.extend(mcp_tools)
                    elif config.type == "custom":
                        # Handle custom toolsets
                        custom_tools = await self._get_custom_tools(name, config)
                        self._tools.extend(custom_tools)
                    logger.debug(f"Loaded tools from toolset '{name}'")
                else:
                    logger.warning(f"No configuration found for toolset '{name}', skipping")
        
        return tools
    
    async def _get_mcp_tools(self, name: str, config: ToolsetConfig) -> list[BaseTool]:
        """Get tools from MCP toolset."""
        try:
            client = MultiServerMCPClient(config.config)
            return await client.get_tools()
        except Exception as e:
            logger.warning(f"Failed to get MCP tools from {name}: {e}")
            return []
    
    async def _get_custom_tools(self, name: str, config: ToolsetConfig) -> list[BaseTool]:
        """Get tools from custom toolset."""
        logger.info(f"Loading custom tools from {name}")
        
        # Handle built-in toolsets
        if name == "file_tools":
            try:
                from runtime.infrastructure.tools.file_tools import get_file_tools
                tools = get_file_tools()
                logger.info(f"Loaded {len(tools)} file manipulation tools")
                return tools
            except Exception as e:
                logger.error(f"Failed to load file tools: {e}")
                return []
        
        elif name == "web_tools":
            try:
                from runtime.infrastructure.tools.web_tools import get_web_tools
                tools = get_web_tools()
                logger.info(f"Loaded {len(tools)} web interaction tools")
                return tools
            except Exception as e:
                logger.error(f"Failed to load web tools: {e}")
                return []
        
        elif name == "essential_tools":
            # Combined essential toolset with file and web tools
            try:
                from runtime.infrastructure.tools.file_tools import get_file_tools
                from runtime.infrastructure.tools.web_tools import get_web_tools
                
                tools = []
                tools.extend(get_file_tools())
                tools.extend(get_web_tools())
                
                logger.info(f"Loaded {len(tools)} essential tools (file + web)")
                return tools
            except Exception as e:
                logger.error(f"Failed to load essential tools: {e}")
                return []
        
        # Handle other custom toolsets from configuration
        tools_directory = config.config.get("tools_directory", "./tools")
        auto_discovery = config.config.get("auto_discovery", False)
        
        if auto_discovery:
            # Future: implement tool discovery from directory
            logger.info(f"Auto-discovery from {tools_directory} not yet implemented")
        
        return []
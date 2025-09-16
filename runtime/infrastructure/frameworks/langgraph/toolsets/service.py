"""LangGraph toolset service implementation.

This module provides toolset services specifically designed for LangGraph agents.
"""

import logging
from typing import Any, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

from runtime.domain.services.toolset.toolset_service import ToolsetService, ToolsetClient

from ..config import ToolsetsConfig, ToolsetConfig

logger = logging.getLogger(__name__)


class LangGraphToolsetService(ToolsetService):
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
    
    async def create_client(self, toolset_names: list[str]) -> "LangGraphToolsetClient":
        """Create a toolset client for LangGraph."""
        return LangGraphToolsetClient(self._toolsets_config, toolset_names)


class LangGraphToolsetClient(ToolsetClient):
    """Toolset client for LangGraph agents."""
    
    def __init__(self, toolsets_config: ToolsetsConfig, toolset_names: list[str]):
        """Initialize with toolsets config and requested toolset names."""
        self.toolsets_config = toolsets_config
        self.toolset_names = toolset_names
        self._tools = None
    
    async def get_tools(self) -> list[Any]:
        """Get LangGraph-compatible tools."""
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
        
        return self._tools
    
    async def _get_mcp_tools(self, name: str, config: ToolsetConfig) -> list[Any]:
        """Get tools from MCP toolset."""
        try:
            client = MultiServerMCPClient(config.config)
            return await client.get_tools()
        except Exception as e:
            logger.warning(f"Failed to get MCP tools from {name}: {e}")
            return []
    
    async def _get_custom_tools(self, name: str, config: ToolsetConfig) -> list[Any]:
        """Get tools from custom toolset."""
        # Implementation would load custom tools
        logger.info(f"Loading custom tools from {name}")
        return []
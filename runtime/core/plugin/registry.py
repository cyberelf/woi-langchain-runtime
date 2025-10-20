"""Plugin registry for storing and accessing discovered plugins.

This module provides a centralized, async-safe registry for all
discovered agent and tool plugins.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from .loader import PluginMetadata

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Async-safe registry for plugin management.
    
    Features:
    - Separate namespaces for agents and tools
    - First-come-wins collision policy with warnings
    - Query interface for lookups and listings
    - Async-safe operations (thread-safe via single event loop)
    
    Note: In async applications, all operations run on the same event loop,
    so we don't need traditional thread locks. The registry uses simple
    dict operations which are atomic at the Python level.
    """
    
    def __init__(self):
        self._agents: Dict[str, PluginMetadata] = {}
        self._tools: Dict[str, PluginMetadata] = {}
        # For async applications, we could use asyncio.Lock if needed,
        # but dict operations are atomic in CPython, so not strictly necessary
        # unless we have complex multi-step operations
        
    def register_agent(self, plugin_id: str, metadata: PluginMetadata) -> None:
        """Register an agent plugin.
        
        Args:
            plugin_id: Unique plugin identifier (template_id)
            metadata: Plugin metadata
        """
        if plugin_id in self._agents:
            existing = self._agents[plugin_id]
            logger.warning(
                f"Agent plugin '{plugin_id}' already registered "
                f"(existing: {existing.file_path}, new: {metadata.file_path}). "
                f"Keeping existing."
            )
            return
        
        self._agents[plugin_id] = metadata
        logger.info(
            f"Registered agent plugin: {plugin_id} "
            f"({metadata.name} v{metadata.version} from {metadata.source})"
        )
    
    def register_tool(self, plugin_id: str, metadata: PluginMetadata) -> None:
        """Register a tool plugin.
        
        Args:
            plugin_id: Unique plugin identifier (tool name)
            metadata: Plugin metadata
        """
        if plugin_id in self._tools:
            existing = self._tools[plugin_id]
            logger.warning(
                f"Tool plugin '{plugin_id}' already registered "
                f"(existing: {existing.file_path}, new: {metadata.file_path}). "
                f"Keeping existing."
            )
            return
        
        self._tools[plugin_id] = metadata
        logger.info(
            f"Registered tool plugin: {plugin_id} "
            f"({metadata.name} v{metadata.version} from {metadata.source})"
        )
    
    def get_agent(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get agent plugin by ID.
        
        Args:
            plugin_id: Plugin identifier (template_id)
            
        Returns:
            PluginMetadata if found, None otherwise
        """
        return self._agents.get(plugin_id)
    
    def get_tool(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get tool plugin by ID.
        
        Args:
            plugin_id: Plugin identifier (tool name)
            
        Returns:
            PluginMetadata if found, None otherwise
        """
        return self._tools.get(plugin_id)
    
    def list_agents(self) -> List[PluginMetadata]:
        """List all registered agent plugins.
        
        Returns:
            List of agent plugin metadata
        """
        return list(self._agents.values())
    
    def list_tools(self) -> List[PluginMetadata]:
        """List all registered tool plugins.
        
        Returns:
            List of tool plugin metadata
        """
        return list(self._tools.values())
    
    def agent_exists(self, plugin_id: str) -> bool:
        """Check if agent plugin exists.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if registered, False otherwise
        """
        return plugin_id in self._agents
    
    def tool_exists(self, plugin_id: str) -> bool:
        """Check if tool plugin exists.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if registered, False otherwise
        """
        return plugin_id in self._tools
    
    def clear(self) -> None:
        """Clear all registered plugins."""
        self._agents.clear()
        self._tools.clear()
        logger.info("Cleared all registered plugins")
    
    def get_stats(self) -> dict:
        """Get registry statistics.
        
        Returns:
            Dict with agent_count and tool_count
        """
        return {
            "agent_count": len(self._agents),
            "tool_count": len(self._tools),
            "total_plugins": len(self._agents) + len(self._tools)
        }


# Global registry instance
_global_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry instance.
    
    Returns:
        The global PluginRegistry singleton
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry

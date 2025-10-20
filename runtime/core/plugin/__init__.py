"""Plugin system for auto-discovery of agents and tools.

This module provides core functionality for discovering and loading
custom agents and tools from configured plugin directories.

Example:
    >>> from runtime.core.plugin import get_plugin_registry
    >>> registry = get_plugin_registry()
    >>> agents = registry.list_agents()
    >>> tools = registry.list_tools()
"""

from .loader import PluginLoader, PluginMetadata
from .registry import PluginRegistry, get_plugin_registry
from .init import initialize_plugin_system

__all__ = [
    "PluginLoader",
    "PluginMetadata",
    "PluginRegistry",
    "get_plugin_registry",
    "initialize_plugin_system",
]

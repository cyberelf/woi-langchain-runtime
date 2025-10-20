"""Plugin system initialization.

This module orchestrates plugin discovery at application startup.
"""

import logging
from pathlib import Path

from runtime.settings import settings
from .loader import PluginLoader
from .registry import get_plugin_registry

logger = logging.getLogger(__name__)


async def initialize_plugin_system() -> None:
    """Initialize plugin system at application startup.
    
    Discovers and registers:
    - Agent plugins from configured directories
    - Tool plugins from configured directories
    
    This function is called once during application startup.
    """
    if not settings.enable_plugin_discovery:
        logger.info("Plugin auto-discovery is disabled")
        return
    
    logger.info("Initializing plugin system...")
    
    # Discover agents
    await discover_agent_plugins()
    
    # Discover tools
    await discover_tool_plugins()
    
    # Log summary
    registry = get_plugin_registry()
    stats = registry.get_stats()
    
    logger.info(
        f"Plugin system initialized: "
        f"{stats['agent_count']} agent(s), "
        f"{stats['tool_count']} tool(s)"
    )


async def discover_agent_plugins() -> None:
    """Discover and register agent plugins from manifest files."""
    # Get plugin directories
    agent_dirs = _get_agent_plugin_dirs()
    
    if not agent_dirs:
        logger.debug("No agent plugin directories configured")
        return
    
    logger.info(f"Loading agent plugins from: {[str(d) for d in agent_dirs]}")
    
    # Import framework-specific validator
    try:
        from runtime.infrastructure.frameworks.langgraph.validators import validate_agent_class
    except ImportError as e:
        logger.error(f"Cannot import LangGraph framework components: {e}")
        return
    
    # Create loader for manifest-based discovery
    loader = PluginLoader(
        plugin_dirs=agent_dirs,
        validator=validate_agent_class,
        plugin_type="agent",
        manifest_attr="__agents__"
    )
    
    # Discover plugins from manifests
    plugins = loader.discover_plugins()
    
    # Register in global registry
    registry = get_plugin_registry()
    for plugin_id, metadata in plugins.items():
        registry.register_agent(plugin_id, metadata)
    
    logger.info(f"Loaded and registered {len(plugins)} agent plugin(s)")


async def discover_tool_plugins() -> None:
    """Discover and register tool plugins from manifest files."""
    # Get plugin directories
    tool_dirs = _get_tool_plugin_dirs()
    
    if not tool_dirs:
        logger.debug("No tool plugin directories configured")
        return
    
    logger.info(f"Loading tool plugins from: {[str(d) for d in tool_dirs]}")
    
    # Import framework-specific validator
    try:
        from runtime.infrastructure.frameworks.langgraph.validators import validate_tool_class
    except ImportError as e:
        logger.error(f"Cannot import tool framework components: {e}")
        return
    
    # Create loader for manifest-based discovery
    loader = PluginLoader(
        plugin_dirs=tool_dirs,
        validator=validate_tool_class,
        plugin_type="tool",
        manifest_attr="__tools__"
    )
    
    # Discover plugins from manifests
    plugins = loader.discover_plugins()
    
    # Register in global registry
    registry = get_plugin_registry()
    for plugin_id, metadata in plugins.items():
        registry.register_tool(plugin_id, metadata)
    
    logger.info(f"Loaded and registered {len(plugins)} tool plugin(s)")


def _get_agent_plugin_dirs() -> list[Path]:
    """Get list of agent plugin directories from settings.
    
    Returns:
        List of Path objects for directories to scan
    """
    dirs = []
    
    # Custom directory (takes precedence)
    if settings.custom_agents_dir:
        custom_dir = Path(settings.custom_agents_dir)
        if custom_dir.exists() and custom_dir.is_dir():
            dirs.append(custom_dir)
        else:
            logger.warning(f"Custom agents directory does not exist: {custom_dir}")
    
    # Default plugin directory
    default_dir = Path(settings.plugin_root_dir) / settings.plugin_agents_dir
    if default_dir.exists() and default_dir.is_dir():
        dirs.append(default_dir)
    
    return dirs


def _get_tool_plugin_dirs() -> list[Path]:
    """Get list of tool plugin directories from settings.
    
    Returns:
        List of Path objects for directories to scan
    """
    dirs = []
    
    # Custom directory (takes precedence)
    if settings.custom_tools_dir:
        custom_dir = Path(settings.custom_tools_dir)
        if custom_dir.exists() and custom_dir.is_dir():
            dirs.append(custom_dir)
        else:
            logger.warning(f"Custom tools directory does not exist: {custom_dir}")
    
    # Default plugin directory
    default_dir = Path(settings.plugin_root_dir) / settings.plugin_tools_dir
    if default_dir.exists() and default_dir.is_dir():
        dirs.append(default_dir)
    
    return dirs

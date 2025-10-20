"""LangGraph template implementations.

This module contains all LangGraph-specific agent templates and provides
utilities for template discovery and management.
"""

from .base import (
    BaseLangGraphAgent,
    BaseLangGraphChatAgent,
    BaseLangGraphTaskAgent,
)
from .simple import SimpleTestAgent
from .workflow import WorkflowAgent

import logging
logger = logging.getLogger(__name__)

# Template registry for this framework
_TEMPLATE_CLASSES = {
    SimpleTestAgent.template_id: SimpleTestAgent,
    WorkflowAgent.template_id: WorkflowAgent,
}

def get_langgraph_templates() -> list[dict]:
    """Get list of available LangGraph templates with metadata (built-in + plugins)."""
    templates = []
    
    # Add built-in templates
    for template_id, template_class in _TEMPLATE_CLASSES.items():
        try:
            # Get template metadata
            metadata = {
                "template_id": template_class.template_id,
                "template_name": template_class.template_name,
                "template_version": template_class.template_version,
                "description": template_class.template_description,
                "framework": "langgraph",
                "source": "built-in",
                "class": template_class,
            }
            templates.append(metadata)
        except Exception as e:
            # Log error but continue with other templates
            import logging
            logging.warning(f"Failed to load built-in template {template_id}: {e}")
    
    # Add plugin templates
    try:
        from runtime.core.plugin import get_plugin_registry
        from runtime.settings import settings
        
        if settings.enable_plugin_discovery:
            registry = get_plugin_registry()
            plugin_agents = registry.list_agents()
            
            for plugin_meta in plugin_agents:
                # Check if plugin would shadow built-in
                if plugin_meta.plugin_id in _TEMPLATE_CLASSES:
                    import logging
                    logging.warning(
                        f"Plugin agent '{plugin_meta.plugin_id}' shadowed by built-in template. "
                        f"Using built-in."
                    )
                    continue
                
                try:
                    template_class = plugin_meta.class_obj
                    metadata = {
                        "template_id": plugin_meta.plugin_id,
                        "template_name": getattr(template_class, 'template_name', plugin_meta.name),
                        "template_version": plugin_meta.version,
                        "description": plugin_meta.description,
                        "framework": "langgraph",
                        "source": "plugin",
                        "file_path": str(plugin_meta.file_path),
                        "class": template_class,
                    }
                    templates.append(metadata)
                except Exception as e:
                    logger.error(f"Failed to load plugin template {plugin_meta.plugin_id}: {e}")
    except ImportError:
        # Plugin system not available (optional dependency)
        logger.warning(f"Error loading plugin templates: {e}")
        pass
    
    return templates


def get_langgraph_template_classes() -> dict[str, type]:
    """Get mapping of template IDs to template classes (built-in + plugins)."""
    classes = _TEMPLATE_CLASSES.copy()
    
    # Add plugin templates
    try:
        from runtime.core.plugin import get_plugin_registry
        from runtime.settings import settings
        
        if settings.enable_plugin_discovery:
            registry = get_plugin_registry()
            plugin_agents = registry.list_agents()
            
            for plugin_meta in plugin_agents:
                # Built-ins take precedence over plugins
                if plugin_meta.plugin_id not in _TEMPLATE_CLASSES:
                    classes[plugin_meta.plugin_id] = plugin_meta.class_obj
    except ImportError as e:
        # Plugin system not available (optional dependency)
        logger.warning(f"Error loading plugin templates: {e}")
        pass
    
    return classes


def register_template(template_id: str, template_class: type) -> None:
    """Register a new LangGraph template."""
    _TEMPLATE_CLASSES[template_id] = template_class


__all__ = [
    "BaseLangGraphAgent",
    "BaseLangGraphChatAgent",
    "BaseLangGraphTaskAgent",
    "SimpleTestAgent",
    "WorkflowAgent",
    "get_langgraph_templates",
    "get_langgraph_template_classes",
    "register_template",
]
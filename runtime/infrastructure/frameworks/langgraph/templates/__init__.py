"""LangGraph template implementations.

This module contains all LangGraph-specific agent templates and provides
utilities for template discovery and management.
"""

from .base import BaseLangGraphAgent
from .simple import SimpleTestAgent
from .workflow import WorkflowAgent

# Template registry for this framework
_TEMPLATE_CLASSES = {
    SimpleTestAgent.template_id: SimpleTestAgent,
    WorkflowAgent.template_id: WorkflowAgent,
}

def get_langgraph_templates() -> list[dict]:
    """Get list of available LangGraph templates with metadata."""
    templates = []
    
    for template_id, template_class in _TEMPLATE_CLASSES.items():
        try:
            # Get template metadata
            metadata = {
                "template_id": template_class.template_id,
                "template_name": template_class.template_name,
                "template_version": template_class.template_version,
                "description": template_class.template_description,
                "framework": "langgraph",
                "class": template_class,
            }
            templates.append(metadata)
        except Exception as e:
            # Log error but continue with other templates
            import logging
            logging.warning(f"Failed to load template {template_id}: {e}")
    
    return templates


def get_langgraph_template_classes() -> dict[str, type]:
    """Get mapping of template IDs to template classes."""
    return _TEMPLATE_CLASSES.copy()


def register_template(template_id: str, template_class: type) -> None:
    """Register a new LangGraph template."""
    _TEMPLATE_CLASSES[template_id] = template_class


__all__ = [
    "BaseLangGraphAgent",
    "SimpleTestAgent",
    "WorkflowAgent",
    "get_langgraph_templates",
    "get_langgraph_template_classes",
    "register_template",
]
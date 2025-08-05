"""Framework integrations for the Agent Runtime.

This module provides pluggable framework integrations that implement
the core runtime interfaces. Each framework is self-contained and
provides its own templates, LLM services, and toolset integrations.

Available frameworks:
- LangGraph: Complete reference implementation
"""

from .base import FrameworkIntegration

# Lazy import to avoid circular dependencies
def _get_langgraph_framework():
    from .langgraph import LangGraphFramework
    return LangGraphFramework

# Framework registry
AVAILABLE_FRAMEWORKS = {
    "langgraph": _get_langgraph_framework,
}


def get_framework(name: str) -> FrameworkIntegration:
    """Get a framework integration by name."""
    if name not in AVAILABLE_FRAMEWORKS:
        raise ValueError(f"Unknown framework: {name}. Available: {list(AVAILABLE_FRAMEWORKS.keys())}")
    
    framework_class = AVAILABLE_FRAMEWORKS[name]()  # Call the lazy loader
    return framework_class()


def list_frameworks() -> list[str]:
    """List available framework names."""
    return list(AVAILABLE_FRAMEWORKS.keys())


__all__ = [
    "FrameworkIntegration",
    "get_framework",
    "list_frameworks",
    "AVAILABLE_FRAMEWORKS",
]
"""Framework executors for the Agent Runtime.

This module provides pluggable framework executors that implement
pure execution interfaces. Each framework is self-contained and
provides stateless execution capabilities.

Available framework executors:
- LangGraph: Complete reference implementation
"""

from .executor_base import FrameworkExecutor

# Lazy import to avoid circular dependencies
def _get_langgraph_executor():
    from .langgraph.executor import LangGraphFrameworkExecutor
    return LangGraphFrameworkExecutor

# Framework executor registry
AVAILABLE_EXECUTORS = {
    "langgraph": _get_langgraph_executor,
}


def get_framework_executor(name: str) -> FrameworkExecutor:
    """Get a framework executor by name."""
    if name not in AVAILABLE_EXECUTORS:
        raise ValueError(f"Unknown framework executor: {name}. Available: {list(AVAILABLE_EXECUTORS.keys())}")
    
    executor_class = AVAILABLE_EXECUTORS[name]()  # Call the lazy loader
    return executor_class()


def list_framework_executors() -> list[str]:
    """List available framework executor names."""
    return list(AVAILABLE_EXECUTORS.keys())


# Backward compatibility - deprecated
def get_framework(name: str):
    """Deprecated: Use get_framework_executor instead."""
    import warnings
    warnings.warn(
        "get_framework is deprecated. Use get_framework_executor instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_framework_executor(name)


__all__ = [
    "FrameworkExecutor",
    "get_framework_executor",
    "list_framework_executors",
    "AVAILABLE_EXECUTORS",
    # Deprecated but kept for backward compatibility
    "get_framework",
]
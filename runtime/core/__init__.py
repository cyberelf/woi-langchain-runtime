"""Core management interfaces for the Agent Runtime framework.

This module provides the foundational interfaces and managers for:
- Template discovery and management
- Agent factory and lifecycle management
- Framework-agnostic agent execution interfaces
- Scheduler and resource management

The design supports multiple underlying frameworks (LangChain, LangGraph, custom, etc.)
through a pluggable architecture.
"""

from .agent_factory import AgentFactory, AgentFactoryInterface
from .discovery import DiscoveryInterface, TemplateDiscovery
from .scheduler import AgentScheduler, SchedulerInterface
from .template_manager import TemplateManager, TemplateRegistry

__all__ = [
    # Template Management
    "TemplateManager",
    "TemplateRegistry",
    "TemplateDiscovery",
    "DiscoveryInterface",
    # Agent Factory
    "AgentFactory",
    "AgentFactoryInterface",
    # Scheduling
    "AgentScheduler",
    "SchedulerInterface",
]

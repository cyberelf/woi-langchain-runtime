"""LangGraph framework integration.

This module provides a complete reference implementation of how to integrate
a framework with the agent runtime. It demonstrates:

- Template management and discovery
- LLM service integration  
- Toolset provider implementation
- Agent factory pattern
- Framework-specific capabilities

This serves as both a production-ready LangGraph integration and a reference
for implementing other framework integrations.
"""

from .framework import LangGraphFramework
from .factory import LangGraphAgentFactory
from .templates import BaseLangGraphAgent, ConversationAgent, SimpleTestAgent

__all__ = [
    "LangGraphFramework",
    "LangGraphAgentFactory", 
    "BaseLangGraphAgent",
    "ConversationAgent",
    "SimpleTestAgent",
]
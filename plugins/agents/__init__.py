"""Agent plugins registry.

This module explicitly declares all available agent plugins.
To add a new agent: import it and add to __agents__ list.
To disable an agent: comment it out from the list.
"""

from .test_agent import TestPluginAgent

# Explicitly registered agents
# Agents will be loaded in the order they appear in this list
__agents__ = [
    TestPluginAgent,
]

__all__ = [
    "__agents__",
]

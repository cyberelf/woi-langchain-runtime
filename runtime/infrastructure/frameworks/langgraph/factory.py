"""LangGraph agent factory implementation.

This module provides the agent factory specifically for LangGraph-based agents.
It demonstrates the framework-specific factory pattern that other frameworks
can follow.
"""

import logging
from typing import Optional

from ...api.models import AgentCreateRequest
from ...orchestration import AgentFactoryInterface
from ...templates.base import BaseAgentTemplate
from .templates import get_langgraph_template_classes

logger = logging.getLogger(__name__)


class LangGraphAgentFactory(AgentFactoryInterface):
    """
    Framework-specific factory for LangGraph agents.

    This factory provides specialized handling for LangGraph-based templates
    and serves as a reference implementation for other framework factories.
    """

    def __init__(self):
        self.active_agents: dict[str, BaseAgentTemplate] = {}
        self._template_classes = None

    @property
    def template_classes(self) -> dict[str, type]:
        """Get available LangGraph template classes."""
        if self._template_classes is None:
            self._template_classes = get_langgraph_template_classes()
        return self._template_classes

    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """Create a LangGraph-based agent."""
        template_id = agent_data.template_id
        
        # Get template class
        if template_id not in self.template_classes:
            available = list(self.template_classes.keys())
            raise ValueError(f"LangGraph template '{template_id}' not found. Available: {available}")

        template_class = self.template_classes[template_id]
        
        # Create agent instance
        try:
            agent = template_class(agent_data)
            self.active_agents[agent_data.id] = agent
            
            logger.info(f"Created LangGraph agent {agent_data.id} using template {template_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create LangGraph agent {agent_data.id}: {e}")
            raise

    def destroy_agent(self, agent_id: str) -> bool:
        """Destroy a LangGraph agent."""
        if agent_id in self.active_agents:
            try:
                # Clean up agent resources if needed
                agent = self.active_agents[agent_id]
                if hasattr(agent, 'cleanup'):
                    agent.cleanup()
            except Exception as e:
                logger.warning(f"Error during agent cleanup: {e}")
            
            del self.active_agents[agent_id]
            logger.info(f"Destroyed LangGraph agent {agent_id}")
            return True
        
        logger.warning(f"LangGraph agent {agent_id} not found for destruction")
        return False

    def get_agent(self, agent_id: str) -> Optional[BaseAgentTemplate]:
        """Get a LangGraph agent."""
        return self.active_agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """List active LangGraph agents."""
        return list(self.active_agents.keys())

    def supports_framework(self, framework: str) -> bool:
        """Check if this factory supports the framework."""
        return framework.lower() in ["langgraph", "langchain"]

    def get_supported_templates(self) -> list[str]:
        """Get list of supported template IDs."""
        return list(self.template_classes.keys())

    def get_health_status(self) -> dict[str, any]:
        """Get factory health status."""
        return {
            "factory_type": "langgraph",
            "active_agents": len(self.active_agents),
            "available_templates": len(self.template_classes),
            "supported_frameworks": ["langgraph", "langchain"],
            "status": "healthy"
        }
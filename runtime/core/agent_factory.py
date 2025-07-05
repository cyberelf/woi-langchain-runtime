"""Agent Factory - Framework-agnostic agent creation and lifecycle management.

This module provides interfaces and implementations for creating and managing
agent instances across different underlying frameworks. It supports:
- Template-based agent creation
- Framework abstraction
- Agent lifecycle management
- Resource allocation and cleanup
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from ..models import AgentCreateRequest
from ..template_agent.base import BaseAgentTemplate
from .template_manager import TemplateManager

logger = logging.getLogger(__name__)


class AgentFactoryInterface(ABC):
    """Interface for agent factory implementations."""

    @abstractmethod
    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """Create an agent instance from template and configuration."""
        pass

    @abstractmethod
    def destroy_agent(self, agent_id: str) -> bool:
        """Destroy an agent instance and clean up resources."""
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[BaseAgentTemplate]:
        """Get an existing agent instance."""
        pass

    @abstractmethod
    def list_agents(self) -> list[str]:
        """List all active agent IDs."""
        pass

    @abstractmethod
    def supports_framework(self, framework: str) -> bool:
        """Check if this factory supports the given framework."""
        pass


class AgentFactory(AgentFactoryInterface):
    """
    Main agent factory with multi-framework support.

    This factory provides:
    - Template-based agent creation
    - Framework detection and routing
    - Agent lifecycle management
    - Resource tracking and cleanup
    """

    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager
        self.active_agents: dict[str, BaseAgentTemplate] = {}
        self.agent_metadata: dict[str, dict[str, Any]] = {}

        # Framework-specific factories
        self.framework_factories: dict[str, AgentFactoryInterface] = {}

        # Resource tracking
        self.creation_timestamps: dict[str, datetime] = {}
        self.agent_metrics: dict[str, dict[str, Any]] = {}

    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """
        Create an agent instance from template and configuration.

        Args:
            agent_data: Agent creation request data

        Returns:
            Agent instance

        Raises:
            ValueError: If agent already exists or template not found
            RuntimeError: If creation fails
        """
        # Check if agent already exists
        if agent_data.id in self.active_agents:
            raise ValueError(f"Agent {agent_data.id} already exists")

        # Get template information
        template_info = self.template_manager.get_template_info(
            agent_data.template_id,
            agent_data.template_version_id,
        )

        if not template_info:
            available_templates = [t.template_id for t in self.template_manager.list_templates()]
            raise ValueError(
                f"Template {agent_data.template_id}:{agent_data.template_version_id} not found. "
                f"Available templates: {available_templates}",
            )

        try:
            # Check if we have a framework-specific factory
            framework = template_info.framework
            framework_factory = self.framework_factories.get(framework)

            if framework_factory:
                # Use framework-specific factory
                agent = framework_factory.create_agent(agent_data)
            else:
                # Use template manager's default creation
                agent = self.template_manager.create_agent(agent_data)

            # Register the agent
            self.active_agents[agent_data.id] = agent
            self.creation_timestamps[agent_data.id] = datetime.now()

            # Store metadata
            self.agent_metadata[agent_data.id] = {
                "template_id": agent_data.template_id,
                "template_version": agent_data.template_version_id,
                "framework": framework,
                "agent_type": agent_data.type,
                "created_at": self.creation_timestamps[agent_data.id].isoformat(),
                "template_config": agent_data.template_config,
                "conversation_config": agent_data.conversation_config,
            }

            # Initialize metrics
            self.agent_metrics[agent_data.id] = {
                "total_executions": 0,
                "total_response_time": 0.0,
                "error_count": 0,
                "last_execution": None,
            }

            logger.info(
                f"Created agent {agent_data.id} using template {agent_data.template_id}:{agent_data.template_version_id}"
            )
            return agent

        except Exception as e:
            logger.error(f"Failed to create agent {agent_data.id}: {e}")
            raise RuntimeError(f"Agent creation failed: {e}")

    def destroy_agent(self, agent_id: str) -> bool:
        """
        Destroy an agent instance and clean up resources.

        Args:
            agent_id: Agent identifier

        Returns:
            True if destruction successful, False if agent not found
        """
        if agent_id not in self.active_agents:
            logger.warning(f"Agent {agent_id} not found for destruction")
            return False

        try:
            agent = self.active_agents[agent_id]

            # Check if agent has cleanup method
            if hasattr(agent, "cleanup"):
                agent.cleanup()

            # Remove from tracking
            del self.active_agents[agent_id]
            del self.creation_timestamps[agent_id]
            del self.agent_metadata[agent_id]
            del self.agent_metrics[agent_id]

            logger.info(f"Destroyed agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to destroy agent {agent_id}: {e}")
            return False

    def get_agent(self, agent_id: str) -> Optional[BaseAgentTemplate]:
        """
        Get an existing agent instance.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None if not found
        """
        return self.active_agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """
        List all active agent IDs.

        Returns:
            List of agent identifiers
        """
        return list(self.active_agents.keys())

    def update_agent(self, agent_id: str, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """
        Update an existing agent with new configuration.

        Args:
            agent_id: Agent identifier
            agent_data: New agent configuration

        Returns:
            Updated agent instance

        Raises:
            ValueError: If agent not found or configuration invalid
        """
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} not found")

        # Destroy old agent
        self.destroy_agent(agent_id)

        # Create new agent with updated configuration
        agent_data.id = agent_id
        return self.create_agent(agent_data)

    def get_agent_metadata(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get metadata for an agent."""
        return self.agent_metadata.get(agent_id)

    def get_agent_metrics(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get metrics for an agent."""
        return self.agent_metrics.get(agent_id)

    def update_agent_metrics(self, agent_id: str, execution_time: float, error: bool = False) -> None:
        """Update execution metrics for an agent."""
        if agent_id in self.agent_metrics:
            metrics = self.agent_metrics[agent_id]
            metrics["total_executions"] += 1
            metrics["total_response_time"] += execution_time
            metrics["last_execution"] = datetime.now().isoformat()

            if error:
                metrics["error_count"] += 1

    def supports_framework(self, framework: str) -> bool:
        """
        Check if this factory supports the given framework.

        Args:
            framework: Framework name

        Returns:
            True if supported, False otherwise
        """
        # This factory supports all frameworks that have templates
        available_frameworks = set()
        for template_info in self.template_manager.list_templates():
            available_frameworks.add(template_info.framework)

        return framework in available_frameworks

    def register_framework_factory(self, framework: str, factory: AgentFactoryInterface) -> None:
        """
        Register a framework-specific factory.

        Args:
            framework: Framework name
            factory: Framework-specific factory implementation
        """
        self.framework_factories[framework] = factory
        logger.info(f"Registered framework factory for {framework}")

    def unregister_framework_factory(self, framework: str) -> None:
        """
        Unregister a framework-specific factory.

        Args:
            framework: Framework name
        """
        if framework in self.framework_factories:
            del self.framework_factories[framework]
            logger.info(f"Unregistered framework factory for {framework}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get factory statistics.

        Returns:
            Dictionary containing factory statistics
        """
        total_agents = len(self.active_agents)

        # Calculate average response time
        total_executions = 0
        total_response_time = 0.0
        total_errors = 0

        for metrics in self.agent_metrics.values():
            total_executions += metrics["total_executions"]
            total_response_time += metrics["total_response_time"]
            total_errors += metrics["error_count"]

        avg_response_time = total_response_time / total_executions if total_executions > 0 else 0.0
        error_rate = total_errors / total_executions if total_executions > 0 else 0.0

        # Framework distribution
        framework_counts = {}
        for metadata in self.agent_metadata.values():
            framework = metadata["framework"]
            framework_counts[framework] = framework_counts.get(framework, 0) + 1

        return {
            "total_agents": total_agents,
            "total_executions": total_executions,
            "average_response_time": avg_response_time,
            "error_rate": error_rate,
            "framework_distribution": framework_counts,
            "active_frameworks": list(self.framework_factories.keys()),
        }

    def cleanup_all(self) -> None:
        """Clean up all agents and resources."""
        agent_ids = list(self.active_agents.keys())
        for agent_id in agent_ids:
            self.destroy_agent(agent_id)

        logger.info("Cleaned up all agents")


class LangChainAgentFactory(AgentFactoryInterface):
    """
    Framework-specific factory for LangChain/LangGraph agents.

    This factory provides specialized handling for LangChain-based templates.
    """

    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager
        self.active_agents: dict[str, BaseAgentTemplate] = {}

    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """Create a LangChain-based agent."""
        # Get template and ensure it's a LangChain template
        template_info = self.template_manager.get_template_info(
            agent_data.template_id,
            agent_data.template_version_id,
        )

        if not template_info or template_info.framework != "langchain":
            raise ValueError(f"Template {agent_data.template_id} is not a LangChain template")

        # Create agent using template
        agent = template_info.template_class.create_instance(agent_data)
        self.active_agents[agent_data.id] = agent

        logger.info(f"Created LangChain agent {agent_data.id}")
        return agent

    def destroy_agent(self, agent_id: str) -> bool:
        """Destroy a LangChain agent."""
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[BaseAgentTemplate]:
        """Get a LangChain agent."""
        return self.active_agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """List LangChain agents."""
        return list(self.active_agents.keys())

    def supports_framework(self, framework: str) -> bool:
        """Check if this factory supports the framework."""
        return framework == "langchain"


class CustomAgentFactory(AgentFactoryInterface):
    """
    Framework-specific factory for custom agents.

    This factory provides specialized handling for custom agent implementations.
    """

    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager
        self.active_agents: dict[str, BaseAgentTemplate] = {}

    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """Create a custom agent."""
        # Get template and ensure it's a custom template
        template_info = self.template_manager.get_template_info(
            agent_data.template_id,
            agent_data.template_version_id,
        )

        if not template_info or template_info.framework != "custom":
            raise ValueError(f"Template {agent_data.template_id} is not a custom template")

        # Create agent using template
        agent = template_info.template_class.create_instance(agent_data)
        self.active_agents[agent_data.id] = agent

        logger.info(f"Created custom agent {agent_data.id}")
        return agent

    def destroy_agent(self, agent_id: str) -> bool:
        """Destroy a custom agent."""
        if agent_id in self.active_agents:
            # Custom agents might need special cleanup
            agent = self.active_agents[agent_id]
            if hasattr(agent, "cleanup"):
                agent.cleanup()

            del self.active_agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[BaseAgentTemplate]:
        """Get a custom agent."""
        return self.active_agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """List custom agents."""
        return list(self.active_agents.keys())

    def supports_framework(self, framework: str) -> bool:
        """Check if this factory supports the framework."""
        return framework == "custom"

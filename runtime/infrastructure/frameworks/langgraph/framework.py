"""LangGraph framework integration implementation.

This provides the complete LangGraph framework integration, serving as both
a production implementation and a reference for other framework integrations.
"""

import logging
from typing import Any, List

from ..base import FrameworkIntegration
from .factory import LangGraphAgentFactory
from .llm import LangGraphLLMService
from .templates import get_langgraph_templates
from .toolsets import LangGraphToolsetService

logger = logging.getLogger(__name__)


class LangGraphFramework(FrameworkIntegration):
    """Complete LangGraph framework integration.
    
    This class provides a reference implementation of how to integrate
    a framework with the agent runtime. It demonstrates all the required
    components and patterns.
    """

    @property
    def name(self) -> str:
        """Framework name."""
        return "langgraph"

    @property
    def version(self) -> str:
        """Framework version."""
        # Could dynamically get this from langgraph.__version__
        return "0.5.1"

    @property
    def description(self) -> str:
        """Framework description."""
        return "LangGraph-based agent framework for stateful, multi-actor applications"

    def get_templates(self) -> List[Any]:
        """Get available LangGraph templates."""
        try:
            return get_langgraph_templates()
        except Exception as e:
            logger.warning(f"Failed to load LangGraph templates: {e}")
            return []

    def create_agent_factory(self) -> LangGraphAgentFactory:
        """Create LangGraph-specific agent factory."""
        return LangGraphAgentFactory()

    def get_llm_service(self) -> LangGraphLLMService:
        """Get LangGraph-specific LLM service."""
        return LangGraphLLMService()

    def get_toolset_service(self) -> LangGraphToolsetService:
        """Get LangGraph-specific toolset service."""
        return LangGraphToolsetService()

    def get_supported_capabilities(self) -> List[str]:
        """Get LangGraph framework capabilities."""
        return [
            "streaming",           # Supports streaming responses
            "tools",              # Supports tool calling
            "memory",             # Supports conversation memory/state
            "multi_agent",        # Supports multi-agent workflows
            "state_management",   # Built-in state management
            "graph_execution",    # Graph-based execution
            "checkpointing",      # Supports execution checkpointing
            "human_in_loop",      # Supports human-in-the-loop patterns
        ]

    async def initialize(self) -> None:
        """Initialize the LangGraph framework."""
        await super().initialize()
        
        logger.info(f"Initializing {self.name} framework v{self.version}")
        
        # Initialize framework-specific components
        templates = self.get_templates()
        logger.info(f"Loaded {len(templates)} LangGraph templates")
        
        # Verify framework dependencies
        try:
            import langgraph
            logger.info(f"LangGraph dependency verified: {langgraph.__version__}")
        except ImportError as e:
            logger.error(f"LangGraph dependency missing: {e}")
            raise
        
        logger.info("LangGraph framework initialized successfully")

    def get_health_status(self) -> dict[str, Any]:
        """Get LangGraph framework health status."""
        status = super().get_health_status()
        
        # Add framework-specific health checks
        try:
            import langgraph
            status["dependencies"] = {
                "langgraph": langgraph.__version__
            }
            status["templates_available"] = len(self.get_templates())
            status["framework_status"] = "healthy"
        except Exception as e:
            status["framework_status"] = "unhealthy"
            status["error"] = str(e)
        
        return status
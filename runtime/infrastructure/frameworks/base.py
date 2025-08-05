"""Base framework integration interface.

This module defines the contract that all framework integrations must implement.
It provides the foundation for pluggable framework support in the agent runtime.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ..core import BaseService
# Avoid circular import - define interface locally
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..orchestration import AgentFactoryInterface


class FrameworkIntegration(BaseService, ABC):
    """Abstract base class for framework integrations.
    
    This defines the contract that all framework implementations must follow.
    Each framework provides its own templates, LLM services, toolsets, and
    agent factory implementations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Framework name (e.g., 'langgraph', 'crewai', 'autogen')."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Framework version."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Framework description."""
        pass

    @abstractmethod
    def get_templates(self) -> List[Any]:
        """Get available templates from this framework.
        
        Returns:
            List of template information objects
        """
        pass

    @abstractmethod
    def create_agent_factory(self) -> Any:
        """Create framework-specific agent factory.
        
        Returns:
            Agent factory that can create agents using this framework
        """
        pass

    @abstractmethod
    def get_llm_service(self) -> Any:
        """Get framework-specific LLM service.
        
        Returns:
            LLM service compatible with this framework
        """
        pass

    @abstractmethod
    def get_toolset_service(self) -> Any:
        """Get framework-specific toolset service.
        
        Returns:
            Toolset service compatible with this framework
        """
        pass

    @abstractmethod
    def get_supported_capabilities(self) -> List[str]:
        """Get list of capabilities supported by this framework.
        
        Returns:
            List of capability names (e.g., 'streaming', 'tools', 'memory')
        """
        pass

    def get_health_status(self) -> Dict[str, Any]:
        """Get framework health status."""
        base_status = super().get_health_status()
        base_status.update({
            "framework": self.name,
            "version": self.version,
            "capabilities": self.get_supported_capabilities(),
        })
        return base_status

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} v{self.version}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"FrameworkIntegration(name='{self.name}', version='{self.version}')"
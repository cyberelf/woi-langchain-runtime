"""Core interfaces and protocols for the Agent Runtime framework.

This module defines fundamental abstractions that serve as the foundation
for the entire runtime architecture. These are dependency-free interfaces
that other layers can implement or depend upon.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class Initializable(Protocol):
    """Protocol for components that require initialization."""
    
    async def initialize(self) -> None:
        """Initialize the component."""
        ...
    
    @property
    def initialized(self) -> bool:
        """Check if component is initialized."""
        ...


@runtime_checkable
class HealthCheckable(Protocol):
    """Protocol for components that support health checks."""
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get component health status."""
        ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for components that can be configured."""
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the component."""
        ...


class BaseService(ABC):
    """Abstract base class for all services in the runtime."""
    
    def __init__(self):
        self._initialized = False
    
    @property
    def initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    async def initialize(self) -> None:
        """Initialize the service. Override in subclasses."""
        self._initialized = True
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status. Override in subclasses."""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "initialized": self._initialized,
        }


class BaseRepository(ABC):
    """Abstract base class for all repositories in the runtime."""
    
    def __init__(self):
        self._initialized = False
    
    @property
    def initialized(self) -> bool:
        """Check if repository is initialized."""
        return self._initialized
    
    async def initialize(self) -> None:
        """Initialize the repository. Override in subclasses."""
        self._initialized = True


class BaseManager(ABC):
    """Abstract base class for all managers in the runtime."""
    
    def __init__(self):
        self._initialized = False
    
    @property
    def initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized
    
    async def initialize(self) -> None:
        """Initialize the manager. Override in subclasses."""
        self._initialized = True
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get manager health status. Override in subclasses."""
        return {
            "status": "healthy" if self._initialized else "not_initialized", 
            "initialized": self._initialized,
        }


class ToolsetServiceInterface(ABC):
    """Abstract interface for toolset services.
    
    This interface defines the contract that all toolset service implementations
    must follow, allowing the framework executor to interact with toolsets in a
    consistent manner across different frameworks.
    """
    
    @abstractmethod
    def get_all_toolset_names(self) -> list[str]:
        """Get all available toolset names.
        
        Returns:
            List of toolset identifiers that can be used by agents.
            Each name represents a toolset that can be requested when
            configuring an agent.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the toolset service and cleanup resources.
        
        This method should be called when the service is no longer needed
        to properly cleanup connections, clients, and other resources.
        """
        pass

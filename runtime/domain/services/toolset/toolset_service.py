"""Domain toolset service interface."""

from abc import ABC, abstractmethod
from typing import Any


class ToolsetClient(ABC):
    """Abstract base class for toolset clients.
    
    Toolset clients provide access to tools from various sources (MCP servers,
    custom implementations, etc.) in a framework-specific format.
    """
    
    @abstractmethod
    async def get_tools(self) -> list[Any]:
        """Get tools in framework-specific format.
        
        Returns:
            List of tools compatible with the target framework
        """
        pass


class ToolsetService(ABC):
    """Abstract base class for toolset services.
    
    Toolset services manage the creation of toolset clients and discovery
    of available toolsets. Each framework should implement this interface
    to provide toolset integration.
    """
    
    @abstractmethod
    async def create_client(self, toolset_names: list[str]) -> ToolsetClient:
        """Create a toolset client from toolset names.
        
        Args:
            toolset_names: List of toolset names to use
            
        Returns:
            Framework-specific toolset client
            
        Note:
            Framework implementations should convert toolset names to
            appropriate configurations internally.
        """
        pass

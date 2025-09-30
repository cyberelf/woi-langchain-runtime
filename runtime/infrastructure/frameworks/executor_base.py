"""Infrastructure Framework Executor Implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

# Import from core interfaces
from ...core.executors import FrameworkExecutorInterface
from ...core.types import ChatMessage
from ...domain.services.template_validation_service import TemplateValidationInterface
from ...core import BaseService


class FrameworkExecutor(BaseService, FrameworkExecutorInterface, TemplateValidationInterface, ABC):
    """Abstract base class for pure framework executors.
    
    This replaces FrameworkIntegration with a purely stateless execution model.
    No instance management - just pure execution functions.
    
    Implements TemplateValidationInterface to provide template validation
    capabilities directly from the executor that manages the templates.
    """


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


    # TemplateValidationInterface implementation
    @abstractmethod
    def validate_template_configuration(
        self, 
        template_id: str, 
        configuration: dict
    ) -> tuple[bool, Optional[ValidationError]]:
        """Validate configuration for a specific template.
        
        Args:
            template_id: The template identifier
            configuration: The configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, validation_error)
            - is_valid: True if configuration is valid
            - validation_error: ValidationError if invalid, None if valid
        """
        pass
    
    @abstractmethod
    def template_exists(self, template_id: str) -> bool:
        """Check if a template exists.
        
        Args:
            template_id: The template identifier to check
            
        Returns:
            True if template exists, False otherwise
        """
        pass

    def get_health_status(self) -> Dict[str, Any]:
        """Get framework health status."""
        base_status = super().get_health_status()
        base_status.update({
            "framework": self.name,
            "version": self.version,
            "capabilities": self.get_supported_capabilities(),
            "executor_type": "stateless",
            "templates": len(self.get_templates())
        })
        return base_status

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} v{self.version} (Executor)"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"FrameworkExecutor(name='{self.name}', version='{self.version}')"


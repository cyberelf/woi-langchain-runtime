"""Template validation interface - Domain layer."""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import ValidationError


class TemplateValidationInterface(ABC):
    """Interface for template validation.
    
    This allows the domain layer to validate templates without depending
    on infrastructure details. The infrastructure layer provides the concrete
    implementation that knows about specific template classes.
    """
    
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


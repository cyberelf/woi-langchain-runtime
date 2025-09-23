"""Base agent template for framework-agnostic agent implementations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

# Services are now framework-specific, no domain abstractions needed
from runtime.infrastructure.web.models.responses import (
    ChatCompletionResponse,
    StreamingChunk,
)
from runtime.domain.value_objects.chat_message import ChatMessage
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.domain.value_objects.template import ConfigField, ConfigFieldValidation


class BaseAgentTemplate(ABC):
    """Base class for all agent templates.
    
    Agent templates define both template metadata (as class variables) 
    and execution logic (as instance methods).
    """

    # Template Metadata (should be overridden in subclasses)
    template_name: str = "Base Agent Template"
    template_id: str = "base-agent"
    template_version: str = "1.0.0"
    template_description: str = "Base agent template"
    framework: str = "base"

    # Placeholder for the configuration schema, should be overridden in subclasses
    config_schema: type[BaseModel] = BaseModel

    def __init__(
        self, 
        configuration: AgentConfiguration, 
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize agent instance with configuration and metadata.
        
        Args:
            configuration: AgentConfiguration value object containing all agent config
            metadata: Static metadata about the agent (id, name, template_id, etc.)
            
        """
        metadata = metadata or {}
        
        # Initialize identity and template fields from metadata
        self.id = metadata.get("agent_id", "unknown")
        self.name = metadata.get("agent_name", "Unknown Agent")
        self.template_id = metadata.get("template_id", self.template_id)
        self.template_version = metadata.get("template_version", self.template_version)
        
        # Store the configuration value object
        self.agent_configuration = configuration
        
        # Get template configuration dict for backward compatibility
        self.template_config = configuration.get_template_configuration()

        self.system_prompt = configuration.system_prompt

    @abstractmethod
    async def execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """Execute the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream execute the agent. Must be implemented by subclasses."""
        pass

    @classmethod
    def get_config_fields(cls) -> list[ConfigField]:
        """Get the configuration fields for the template as domain objects."""
        # Get the standard Pydantic JSON schema
        pydantic_schema = cls.config_schema.model_json_schema()
        
        # Convert to ConfigField domain objects
        config_fields = []
        properties = pydantic_schema.get("properties", {})
        
        for field_key, field_info in properties.items():
            # Extract field type
            field_type = field_info.get("type", "string")
            
            # Create validation object if needed
            validation = None
            validation_dict = {}
            if "minLength" in field_info:
                validation_dict["minLength"] = field_info["minLength"]
            if "maxLength" in field_info:
                validation_dict["maxLength"] = field_info["maxLength"]
            if "minimum" in field_info:
                validation_dict["min"] = field_info["minimum"]
            if "maximum" in field_info:
                validation_dict["max"] = field_info["maximum"]
            if "pattern" in field_info:
                validation_dict["pattern"] = field_info["pattern"]
            if "enum" in field_info:
                validation_dict["enum"] = field_info["enum"]
            
            if validation_dict:
                validation = ConfigFieldValidation.from_dict(validation_dict)
            
            # Create ConfigField domain object
            config_field = ConfigField(
                key=field_key,
                field_type=field_type,
                description=field_info.get("description"),
                default_value=field_info.get("default"),
                validation=validation
            )
            
            config_fields.append(config_field)
        
        return config_fields

    @classmethod
    def validate_configuration(cls, configuration: dict[str, Any]) -> tuple[bool, Optional[ValidationError]]:
        """Validate the configuration for the template."""
        try:
            cls.config_schema.model_validate(configuration)
            return True, None
        except ValidationError as e:
            return False, e

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from template_config.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check template_config first for backward compatibility
        if key in self.template_config:
            return self.template_config[key]
        
        # Then check AgentConfiguration's template_config
        return self.agent_configuration.get_template_config_value(key, default)
    

    def cleanup(self):
        """Clean up agent resources if needed."""
        pass

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.template_name} ({self.id})"

    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return f"BaseAgentTemplate(id='{self.id}', template_id='{self.template_id}')"


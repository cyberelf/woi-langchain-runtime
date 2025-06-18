"""Base Agent Template - Enhanced Agent with Template Metadata."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from pydantic import BaseModel

from ..models import AgentCreateRequest, AgentType


@dataclass
class TemplateMetadata:
    """Template metadata extracted from agent class."""
    name: str
    template_id: str
    version: str
    description: str
    agent_type: AgentType
    config_schema: Dict[str, Any]
    runtime_requirements: Dict[str, Any]


@dataclass  
class ValidationResult:
    """Template configuration validation result."""
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseAgentTemplate(ABC):
    """
    Base class for agent templates.
    
    Agent classes ARE templates - they contain both template metadata 
    (as class variables) and execution logic (as instance methods).
    """
    
    # Template Metadata (class variables)
    template_name: str = "Base Agent Template"
    template_id: str = "base-agent"
    template_version: str = "1.0.0"
    template_description: str = "Base agent template"
    agent_type: AgentType = AgentType.CONVERSATION
    
    # Configuration Schema (class variable)
    config_schema: Dict[str, Any] = {}
    
    # Runtime Requirements (class variable)
    runtime_requirements: Dict[str, Any] = {
        "memory": "256MB",
        "cpu": "0.1 cores",
        "gpu": False,
        "estimatedLatency": "< 2s"
    }
    
    @classmethod
    def get_metadata(cls) -> TemplateMetadata:
        """Get template metadata from class variables."""
        return TemplateMetadata(
            name=cls.template_name,
            template_id=cls.template_id,
            version=cls.template_version,
            description=cls.template_description,
            agent_type=cls.agent_type,
            config_schema=cls.config_schema,
            runtime_requirements=cls.runtime_requirements
        )
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration against template schema.
        
        Override in subclasses for custom validation logic.
        """
        errors = []
        warnings = []
        
        # Basic validation against schema
        for field_name, field_schema in cls.config_schema.items():
            if field_schema.get('required', False) and field_name not in config:
                errors.append(f"Required field '{field_name}' is missing")
            
            if field_name in config:
                value = config[field_name]
                field_type = field_schema.get('type')
                
                # Type validation
                if field_type == 'integer' and not isinstance(value, int):
                    errors.append(f"Field '{field_name}' must be an integer")
                elif field_type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Field '{field_name}' must be a boolean")
                elif field_type == 'string' and not isinstance(value, str):
                    errors.append(f"Field '{field_name}' must be a string")
                
                # Range validation
                if isinstance(value, (int, float)):
                    min_val = field_schema.get('minimum')
                    max_val = field_schema.get('maximum')
                    if min_val is not None and value < min_val:
                        errors.append(f"Field '{field_name}' must be >= {min_val}")
                    if max_val is not None and value > max_val:
                        errors.append(f"Field '{field_name}' must be <= {max_val}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    @classmethod
    def create_instance(cls, agent_data: AgentCreateRequest) -> 'BaseAgentTemplate':
        """
        Create agent instance from configuration.
        
        This replaces the factory pattern - the class creates itself.
        """
        # Validate config first
        validation = cls.validate_config(agent_data.template_config)
        if not validation.valid:
            raise ValueError(f"Invalid configuration: {validation.errors}")
        
        # Create instance
        return cls(agent_data)
    
    def __init__(self, agent_data: AgentCreateRequest) -> None:
        """Initialize agent instance with configuration."""
        self.id = agent_data.id
        self.name = agent_data.name
        self.description = agent_data.description
        self.template_config = agent_data.template_config
        self.system_prompt = agent_data.system_prompt
        self.conversation_config = agent_data.conversation_config or {}
        self.toolsets = agent_data.toolsets  # Selected toolsets
        self.llm_config_id = agent_data.llm_config_id
        
        # Execution metrics
        self.total_executions = 0
        self.total_response_time = 0.0
        self.error_count = 0
        
        # Build the agent graph
        self.graph = self._build_graph()
    
    @abstractmethod
    def _build_graph(self):
        """Build the LangGraph execution graph. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def execute(self, messages, stream=False, temperature=None, max_tokens=None, metadata=None):
        """Execute the agent. Must be implemented by subclasses."""
        pass


def get_all_agent_templates() -> List[Type[BaseAgentTemplate]]:
    """
    Get all registered agent template classes using introspection.
    
    This uses Python's class hierarchy to discover all agent templates.
    """
    def get_subclasses(cls):
        """Recursively get all subclasses."""
        subclasses = set(cls.__subclasses__())
        for subclass in list(subclasses):
            subclasses.update(get_subclasses(subclass))
        return subclasses
    
    return list(get_subclasses(BaseAgentTemplate))


def get_template_by_id(template_id: str) -> Optional[Type[BaseAgentTemplate]]:
    """Get agent template class by template ID."""
    for template_class in get_all_agent_templates():
        if template_class.template_id == template_id:
            return template_class
    return None 
"""Base Agent Template - Enhanced Agent with Template Metadata."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.language_models.base import BaseLanguageModel

from pydantic import BaseModel, ValidationError

from runtime.toolset.toolset_service import ToolsetClient, ToolsetService

from ..models import (AgentCreateRequest, ChatCompletionChunk,
                      ChatCompletionResponse, ChatMessage)


@dataclass
class TemplateMetadata:
    """Template metadata extracted from agent class."""

    name: str
    template_id: str
    version: str
    description: str
    config_schema: type[BaseModel]


@dataclass
class ValidationResult:
    """Template configuration validation result."""

    valid: bool
    errors: list[str] = None
    warnings: list[str] = None

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

    # Configuration Schema (class variable)
    config_schema: type[BaseModel] = BaseModel

    @classmethod
    def get_metadata(cls) -> TemplateMetadata:
        """Get template metadata from class variables."""
        return TemplateMetadata(
            name=cls.template_name,
            template_id=cls.template_id,
            version=cls.template_version,
            description=cls.template_description,
            config_schema=cls.config_schema,
        )

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> ValidationResult:
        """
        Validate configuration against template schema.

        Override in subclasses for custom validation logic.
        """
        errors = []
        warnings = []

        # Basic validation against schema
        try:
            cls.config_schema.model_validate(config)
        except ValidationError as e:
            errors.append(str(e))

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    @classmethod
    def create_instance(
        cls, 
        agent_data: AgentCreateRequest, 
        llm_service: Optional[Any] = None,
        toolset_service: Optional[ToolsetService] = None
    ) -> "BaseAgentTemplate":
        """
        Create agent instance from configuration.

        This replaces the factory pattern - the class creates itself.
        """
        # Validate config first
        validation = cls.validate_config(agent_data.template_config)
        if not validation.valid:
            raise ValueError(f"Invalid configuration: {validation.errors}")
        # Create instance
        return cls(agent_data, llm_service, toolset_service)

    def __init__(self, agent_data: AgentCreateRequest, llm_service: Any, toolset_service: ToolsetService) -> None:
        """Initialize agent instance with configuration."""
        self.id = agent_data.id
        self.name = agent_data.name
        self.description = agent_data.description
        self.template_config = agent_data.template_config
        self.system_prompt = agent_data.system_prompt
        self.conversation_config = agent_data.conversation_config or {}
        self.toolset_names = agent_data.toolsets
        self.llm_config_id = agent_data.llm_config_id
        self.llm_service = llm_service
        self.toolset_service = toolset_service

        # LLM client will be created lazily
        self.llm_client: Optional[BaseLanguageModel] = None
        self.toolset_client = None

        # Execution metrics
        self.total_executions = 0
        self.total_response_time = 0.0
        self.error_count = 0

    @abstractmethod
    async def execute(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse:
        """Execute the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream the agent. Must be implemented by subclasses."""
        pass

    async def get_llm_client(self) -> BaseLanguageModel:
        """Get the LLM client."""
        if self.llm_client is None:
            self.llm_client = await self.llm_service.get_client(self.llm_config_id)
        return self.llm_client

    async def get_toolset_client(self) -> ToolsetClient:
        """Get the toolset client."""
        if len(self.toolset_names) == 0:
            return None
        if self.toolset_client is None:
            self.toolset_client = await self.toolset_service.get_toolset_client(self.toolset_names)
        return self.toolset_client


def get_all_agent_templates() -> list[type[BaseAgentTemplate]]:
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


def get_template_by_id(template_id: str) -> Optional[type[BaseAgentTemplate]]:
    """Get agent template class by template ID."""
    for template_class in get_all_agent_templates():
        if template_class.template_id == template_id:
            return template_class
    return None

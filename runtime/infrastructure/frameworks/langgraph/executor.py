"""LangGraph Pure Executor Implementation - Stateless Agent Execution."""

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

from pydantic import ValidationError

from .config import LangGraphFrameworkConfig
from runtime.service_config import get_services_config
from .templates.base import BaseLangGraphAgent
from runtime.domain.value_objects.template import TemplateInfo

from ....core.executors import (
    AgentExecutorInterface,
    ExecutionResult,
    StreamingChunk,
)
from ..executor_base import FrameworkExecutor
from ....core.types import ChatMessage
from .templates import get_langgraph_template_classes
from runtime.infrastructure.frameworks.langgraph.llm.service import (
    LangGraphLLMService,
)
from runtime.infrastructure.frameworks.langgraph.toolsets.service import (
    LangGraphToolsetService,
)
from runtime.domain.value_objects.agent_configuration import AgentConfiguration

logger = logging.getLogger(__name__)


class LangGraphAgentExecutor(AgentExecutorInterface):
    """Pure LangGraph agent executor - stateless execution only."""
    
    def __init__(
        self, 
        template_classes: dict[str, type[BaseLangGraphAgent]], 
        llm_service=None, 
        toolset_service=None
    ):
        self.template_classes = template_classes
        self._llm_service = llm_service
        self._toolset_service = toolset_service
    
    async def cleanup(self):
        """Clean up executor resources."""
        # Base cleanup - subclasses can override for specific cleanup logic
        pass
    
    async def execute(
        self,
        template_id: str,
        template_version: str,
        configuration: dict,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> ExecutionResult:
        """Execute agent with given parameters - stateless execution."""
        start_time = time.time()
        
        try:
            # Validate template
            if template_id not in self.template_classes:
                available = list(self.template_classes.keys())
                return ExecutionResult(
                    success=False,
                    error=f"Template '{template_id}' not found. Available: {available}",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Get template class
            template_class = self.template_classes[template_id]
            
            # Create temporary execution instance (not stored/managed)
            execution_instance = self._create_execution_instance(
                template_class, template_id, template_version, configuration, metadata or {}
            )
            
            # Execute with the instance
            # Use configuration defaults if parameters are None
            final_temperature = temperature
            final_max_tokens = max_tokens
            
            # Fallback to configuration defaults if parameters not specified
            if final_temperature is None:
                final_temperature = configuration.get("temperature", 0.7)
            if final_max_tokens is None:
                final_max_tokens = configuration.get("max_tokens")
                
            # Execute and get ExecutionResult directly from template
            result = await execution_instance.execute(
                messages=messages,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                metadata={
                    'template_id': template_id,
                    'template_version': template_version,
                    **(metadata or {})
                }
            )
            
            return result
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"LangGraph execution failed: {e}")
            
            return ExecutionResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time,
                metadata={'template_id': template_id, 'framework': 'langgraph'}
            )
    
    async def stream_execute(
        self,
        template_id: str,
        template_version: str,
        configuration: dict,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream execute agent with given parameters - stateless execution."""
        try:
            # Validate template
            if template_id not in self.template_classes:
                available = list(self.template_classes.keys())
                yield StreamingChunk(
                    content="",
                    finish_reason="error",
                    metadata={'error': f"Template '{template_id}' not found. Available: {available}"}
                )
                return
            
            # Get template class
            template_class = self.template_classes[template_id]
            
            # Create temporary execution instance
            execution_instance = self._create_execution_instance(
                template_class, template_id, template_version, configuration, metadata or {}
            )
            
            # Use configuration defaults if parameters are None
            final_temperature = temperature
            final_max_tokens = max_tokens
            
            # Fallback to configuration defaults if parameters not specified
            if final_temperature is None:
                final_temperature = configuration.get("temperature", 0.7)
            if final_max_tokens is None:
                final_max_tokens = configuration.get("max_tokens")
            
            # Stream execution - templates now return StreamingChunk directly
            async for chunk in execution_instance.stream_execute(
                messages=messages,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                metadata={
                    'template_id': template_id,
                    'template_version': template_version,
                    **(metadata or {})
                }
            ):
                yield chunk
            
                    
        except Exception as e:
            logger.error(f"LangGraph streaming execution failed: {e}")
            yield StreamingChunk(
                content="",
                finish_reason="error",
                metadata={'error': str(e), 'template_id': template_id}
            )
    
    def validate_configuration(
        self,
        template_id: str,
        template_version: str,
        configuration: dict
    ) -> tuple[bool, Optional[ValidationError]]:
        """Validate agent configuration for template."""        
        # Check template exists
        if template_id not in self.template_classes:
            available = list(self.template_classes.keys())
            raise ValueError(f"Template '{template_id}' not found. Available: {available}")
        
        template_class = self.template_classes[template_id]
        
        return template_class.validate_configuration(configuration)
    
    def get_supported_templates(self) -> list[dict]:
        """Get list of supported templates."""
        templates = []
        
        for template_id, template_class in self.template_classes.items():
            # Get the config fields as domain objects
            config_fields = template_class.get_config_fields()
            
            # Create TemplateInfo using domain model
            template_info = TemplateInfo.create_langgraph_template(
                id=template_id,
                name=template_class.template_name,
                description=template_class.template_description,
                version=template_class.template_version,
                config_fields=config_fields
            )
            
            # Convert to dictionary for backward compatibility with existing API contracts
            templates.append(template_info.to_dict())
        
        return templates
    
    def _create_execution_instance(
        self,
        template_class: type,
        template_id: str,
        template_version: str,
        configuration: dict,
        metadata: dict[str, Any]
    ) -> BaseLangGraphAgent:
        """Create a temporary execution instance (not stored/managed)."""
        
        # Prepare static metadata for the template
        static_metadata = {
            "template_id": template_id,
            "template_version": template_version,
            # Extract agent metadata from the execution metadata if available
            "agent_id": metadata.get("agent_id", f"exec-{uuid.uuid4()}"),
            "agent_name": metadata.get("agent_name", f"Execution Instance ({template_id})"),
        }
        
        # Convert dict configuration back to AgentConfiguration for templates
        # The configuration dict comes from AgentConfiguration.get_template_configuration()
        # We need to reconstruct the AgentConfiguration from this dict
        
        # Extract components from the merged configuration dict
        system_prompt = configuration.get("system_prompt")
        llm_config_id = configuration.get("llm_config_id")
        toolsets = configuration.get("toolset_configs", [])
        
        # Extract conversation config parameters
        conversation_config = {}
        if "temperature" in configuration:
            conversation_config["temperature"] = configuration["temperature"]
        if "max_tokens" in configuration:
            conversation_config["max_tokens"] = configuration["max_tokens"]
        if "history_length" in configuration:
            conversation_config["historyLength"] = configuration["history_length"]
        
        # Extract template-specific config (everything else)
        template_config = {k: v for k, v in configuration.items() 
                         if k not in {"system_prompt", "llm_config_id", "toolset_configs", 
                                    "temperature", "max_tokens", "history_length"}}
        
        # Reconstruct AgentConfiguration
        agent_config = AgentConfiguration(
            system_prompt=system_prompt,
            llm_config_id=llm_config_id,
            conversation_config=conversation_config if conversation_config else None,
            toolsets=toolsets,
            template_config=template_config
        )
        
        # Create temporary instance with services injected
        return template_class(
            configuration=agent_config, 
            metadata=static_metadata,
            llm_service=self._llm_service,
            toolset_service=self._toolset_service
        )


class LangGraphFrameworkExecutor(FrameworkExecutor):
    """LangGraph framework executor - pure execution without instance management."""
    
    def __init__(self, service_config=None):
        """Initialize with optional service configuration.
        
        Args:
            service_config: Service configuration data from application layer
        """
        super().__init__()
        self._template_classes = None
        self._agent_executor = None
        self._llm_service = None
        self._toolset_service = None
        self._framework_config: LangGraphFrameworkConfig
        
        # Validate and store configuration during initialization
        self._initialize_configuration(service_config)
    
    def _initialize_configuration(self, service_config):
        """Initialize and validate framework configuration."""
        
        
        try:
            # Get configuration data
            if service_config:
                config_data = service_config
            else:
                # Use global services config
                services_config = get_services_config()
                config_data = {
                    "llm": services_config.get_llm_config(),
                    "toolsets": services_config.get_toolsets_config()
                }
            
            # Validate configuration using pydantic models
            self._framework_config = LangGraphFrameworkConfig.from_dict(config_data)
            logger.info("LangGraph framework configuration validated successfully")
                
        except Exception as e:
            logger.error(f"Failed to validate LangGraph framework configuration: {e}")
            raise e
    
    @property
    def name(self) -> str:
        """Framework name."""
        return "langgraph"
    
    @property
    def version(self) -> str:
        """Framework version."""
        return "0.2.16"
    
    @property
    def description(self) -> str:
        """Framework description."""
        return "LangGraph - Build resilient language agents as graphs"
    
    @property
    def template_classes(self) -> dict:
        """Get available LangGraph template classes."""
        if self._template_classes is None:
            self._template_classes = get_langgraph_template_classes()
        return self._template_classes
    
    @property
    def agent_executor(self) -> AgentExecutorInterface:
        """Create framework-specific agent executor."""
        if self._agent_executor is None:
            self._agent_executor = LangGraphAgentExecutor(
                self.template_classes,
                llm_service=self.get_llm_service(),
                toolset_service=self.get_toolset_service()
            )
        return self._agent_executor
    
    def get_templates(self) -> list[dict]:
        """Get available templates from this framework."""
        return self.agent_executor.get_supported_templates()
    
    def get_llm_service(self) -> Any:
        """Get framework-specific LLM service with validated configuration."""        
        if self._llm_service is None:
            try:
                # Pass validated pydantic config class directly
                self._llm_service = LangGraphLLMService(self._framework_config.llm)
                logger.info("LangGraph LLM service initialized with validated pydantic configuration")
            except ImportError:
                logger.warning("LangGraph LLM service not available")
                self._llm_service = None
            except Exception as e:
                logger.error(f"Failed to initialize LangGraph LLM service: {e}")
                self._llm_service = None
        return self._llm_service
    
    def get_toolset_service(self) -> Any:
        """Get framework-specific toolset service with validated configuration."""
        if self._toolset_service is None:
            try:
                # Pass validated pydantic config class directly
                self._toolset_service = LangGraphToolsetService(self._framework_config.toolsets)
                logger.info("LangGraph toolset service initialized with validated pydantic configuration")
            except ImportError:
                logger.warning("LangGraph toolset service not available")
                self._toolset_service = None
            except Exception as e:
                logger.error(f"Failed to initialize LangGraph toolset service: {e}")
                self._toolset_service = None
        return self._toolset_service
    
    def get_supported_capabilities(self) -> list[str]:
        """Get list of capabilities supported by this framework."""
        return [
            "streaming",
            "state_management", 
            "graph_workflows",
            "tools",
            "memory",
            "conditional_edges",
            "parallel_execution",
            "checkpointing",
            "human_in_the_loop"
        ]
    
    async def initialize(self) -> None:
        """Initialize the framework executor."""
        await super().initialize()
        logger.info(f"Initialized {self.name} executor with {len(self.template_classes)} templates")
    
    async def shutdown(self) -> None:
        """Shutdown the framework executor."""
        # Clean up any resources
        if self._llm_service:
            await self._llm_service.shutdown()
        
        if self._toolset_service:
            await self._toolset_service.shutdown()
        
        logger.info(f"Shutdown {self.name} executor")
    
    def get_health_status(self) -> dict:
        """Get framework health status."""
        status = super().get_health_status()
        status.update({
            "templates_loaded": len(self.template_classes),
            "llm_service_available": self._llm_service is not None,
            "toolset_service_available": self._toolset_service is not None,
            "executor_initialized": self._agent_executor is not None
        })
        return status

    # TemplateValidationInterface implementation
    def validate_template_configuration(
        self, 
        template_id: str, 
        configuration: dict
    ) -> tuple[bool, Optional[ValidationError]]:
        """Validate configuration for a specific template.
        
        Uses the template class's own validation method directly.
        """
        # Check template exists
        if template_id not in self.template_classes:
            # Let the calling code handle the ValueError for non-existent templates
            available = list(self.template_classes.keys())
            raise ValueError(f"Template '{template_id}' not found. Available: {available}")
        
        template_class = self.template_classes[template_id]

        return template_class.validate_configuration(configuration)
    
    def template_exists(self, template_id: str) -> bool:
        """Check if a template exists.
        
        Checks the loaded template classes.
        """
        return template_id in self.template_classes
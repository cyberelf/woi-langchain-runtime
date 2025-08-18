"""LangGraph Pure Executor Implementation - Stateless Agent Execution."""

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

from runtime.templates.base import BaseAgentTemplate

from ..executor_base import (
    AgentExecutorInterface,
    ExecutionResult,
    FrameworkExecutor,
    StreamingChunk,
)
from ....domain.value_objects.chat_message import ChatMessage
from .templates import get_langgraph_template_classes
from runtime.infrastructure.frameworks.langgraph.llm.service import (
    LangGraphLLMService,
)
from runtime.infrastructure.frameworks.langgraph.toolsets.service import (
    LangGraphToolsetService,
)

logger = logging.getLogger(__name__)


class LangGraphAgentExecutor(AgentExecutorInterface):
    """Pure LangGraph agent executor - stateless execution only."""
    
    def __init__(self, template_classes: dict, llm_service=None, toolset_service=None):
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
                template_class, template_id, template_version, configuration, metadata
            )
            
            # Execute with the instance
            response = await execution_instance.execute(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata=metadata or {}
            )
            
            # Convert response to standard format
            processing_time = int((time.time() - start_time) * 1000)
            
            # Extract response data (framework-specific)
            message = "No response"
            finish_reason = "stop"
            prompt_tokens = 0
            completion_tokens = 0
            
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message.content
                finish_reason = getattr(response.choices[0], 'finish_reason', 'stop')
            elif hasattr(response, 'content'):
                message = response.content
            elif isinstance(response, str):
                message = response
            
            if hasattr(response, 'usage'):
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
            else:
                # Estimate tokens
                prompt_tokens = sum(len(msg.content.split()) for msg in messages)
                completion_tokens = len(message.split())
            
            return ExecutionResult(
                success=True,
                message=message,
                finish_reason=finish_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                processing_time_ms=processing_time,
                metadata={
                    'template_id': template_id,
                    'template_version': template_version,
                    'framework': 'langgraph',
                    **(metadata or {})
                }
            )
            
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
                template_class, template_id, template_version, configuration, metadata
            )
            
            # Check if template supports streaming
            if hasattr(execution_instance, 'stream_execute'):
                chunk_index = 0
                async for chunk in execution_instance.stream_execute(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    metadata=metadata or {}
                ):
                    # Convert framework chunk to our format
                    content = ""
                    finish_reason = None
                    
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        content = getattr(delta, 'content', '')
                        finish_reason = getattr(chunk.choices[0], 'finish_reason', None)
                    elif hasattr(chunk, 'content'):
                        content = chunk.content
                    elif isinstance(chunk, str):
                        content = chunk
                    
                    yield StreamingChunk(
                        content=content,
                        chunk_index=chunk_index,
                        finish_reason=finish_reason,
                        metadata={
                            'template_id': template_id,
                            'framework': 'langgraph',
                            **(metadata or {})
                        }
                    )
                    
                    chunk_index += 1
            else:
                # Fallback: simulate streaming from regular execution
                result = await self.execute(
                    template_id, template_version, configuration, messages,
                    temperature, max_tokens, metadata
                )
                
                if result.success and result.message:
                    # Split message into chunks for simulation
                    words = result.message.split()
                    chunk_size = max(1, len(words) // 10)  # Approximately 10 chunks
                    
                    for i in range(0, len(words), chunk_size):
                        chunk_words = words[i:i + chunk_size]
                        content = ' '.join(chunk_words)
                        if i > 0:
                            content = ' ' + content  # Add space for continuation
                        
                        finish_reason = None
                        if i + chunk_size >= len(words):
                            finish_reason = "stop"
                        
                        yield StreamingChunk(
                            content=content,
                            chunk_index=i // chunk_size,
                            finish_reason=finish_reason,
                            metadata={
                                'template_id': template_id,
                                'framework': 'langgraph',
                                'simulated_streaming': True,
                                **(metadata or {})
                            }
                        )
                else:
                    yield StreamingChunk(
                        content="",
                        finish_reason="error",
                        metadata={'error': result.error or 'Execution failed'}
                    )
                    
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
    ) -> tuple[bool, list[str]]:
        """Validate agent configuration for template."""
        errors = []
        
        # Check template exists
        if template_id not in self.template_classes:
            available = list(self.template_classes.keys())
            errors.append(f"Template '{template_id}' not found. Available: {available}")
            return False, errors
        
        template_class = self.template_classes[template_id]
        
        # Template-specific validation
        try:
            # Try to create a validation instance
            temp_instance = self._create_execution_instance(
                template_class, template_id, template_version, configuration, {}
            )
            
            # If template has validate method, use it
            if hasattr(temp_instance, 'validate_configuration'):
                valid, template_errors = temp_instance.validate_configuration(configuration)
                if not valid:
                    errors.extend(template_errors)
            
        except Exception as e:
            errors.append(f"Configuration validation failed: {str(e)}")
        
        return len(errors) == 0, errors
    
    def get_supported_templates(self) -> list[dict]:
        """Get list of supported templates."""
        templates = []
        
        for template_id, template_class in self.template_classes.items():
            template_info = {
                'template_id': template_id,
                'template_name': getattr(template_class, 'name', template_id),
                'description': getattr(template_class, 'description', ''),
                'version': getattr(template_class, 'version', '1.0.0'),
                'capabilities': getattr(template_class, 'capabilities', []),
                'config_schema': getattr(template_class, 'config_schema', {}),
                'framework': 'langgraph'
            }
            templates.append(template_info)
        
        return templates
    
    def _create_execution_instance(
        self,
        template_class: type,
        template_id: str,
        template_version: str,
        configuration: dict,
        metadata: Optional[dict]
    ) -> BaseAgentTemplate:
        """Create a temporary execution instance (not stored/managed)."""
        
        # Prepare static metadata for the template
        static_metadata = {
            "template_id": template_id,
            "template_version": template_version,
            # Extract agent metadata from the execution metadata if available
            "agent_id": metadata.get("agent_id", f"exec-{uuid.uuid4()}"),
            "agent_name": metadata.get("agent_name", f"Execution Instance ({template_id})"),
        }
        
        # Create temporary instance with services injected
        return template_class(
            configuration=configuration, 
            metadata=static_metadata,
            llm_service=self._llm_service,
            toolset_service=self._toolset_service
        )


class LangGraphFrameworkExecutor(FrameworkExecutor):
    """LangGraph framework executor - pure execution without instance management."""
    
    def __init__(self):
        super().__init__()
        self._template_classes = None
        self._agent_executor = None
        self._llm_service = None
        self._toolset_service = None
    
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
    
    def create_agent_executor(self) -> AgentExecutorInterface:
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
        return self.create_agent_executor().get_supported_templates()
    
    def get_llm_service(self) -> Any:
        """Get framework-specific LLM service."""
        if self._llm_service is None:
            # Initialize LangGraph LLM service
            try:
                self._llm_service = LangGraphLLMService()
            except ImportError:
                logger.warning("LangGraph LLM service not available")
                self._llm_service = None
        return self._llm_service
    
    def get_toolset_service(self) -> Any:
        """Get framework-specific toolset service."""
        if self._toolset_service is None:
            # Initialize LangGraph toolset service
            try:
                self._toolset_service = LangGraphToolsetService()
            except ImportError:
                logger.warning("LangGraph toolset service not available")
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
        if self._llm_service and hasattr(self._llm_service, 'shutdown'):
            await self._llm_service.shutdown()
        
        if self._toolset_service and hasattr(self._toolset_service, 'shutdown'):
            await self._toolset_service.shutdown()
        
        await super().shutdown()
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
"""LangGraph Base Agent Template - Framework-specific base class."""

from curses import meta
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Literal, Optional, TypeVar
from datetime import datetime, UTC

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, BaseMessageChunk
from langgraph.graph.state import CompiledStateGraph

from runtime.core.executors import ExecutionResult, StreamingChunk
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.domain.value_objects.template import ConfigField, ConfigFieldValidation

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Type variable for state management
StateType = TypeVar('StateType')


class BaseLangGraphAgent(ABC):
    """
    Base class for LangGraph agent templates.

    Provides common functionality for LangGraph-based agents including:
    - Template metadata and configuration handling
    - Message conversion utilities
    - State creation interface
    - Common execution patterns
    - LLM client integration
    """

    # Template Metadata (should be overridden in subclasses)
    template_name: str = "Base LangGraph Agent Template"
    template_id: str = "base-langgraph-agent"
    template_version: str = "1.0.0"
    template_description: str = "Base LangGraph agent template"
    framework: str = "langgraph"

    # Placeholder for the configuration schema, should be overridden in subclasses
    config_schema: type[BaseModel] = BaseModel

    def __init__(
        self, 
        configuration: AgentConfiguration, 
        llm_service: LangGraphLLMService, 
        toolset_service: Optional[LangGraphToolsetService] = None, 
        metadata: Optional[dict[str, Any]] = None
    ):
        """Initialize LangGraph agent instance with configuration and metadata.
        
        Args:
            configuration: AgentConfiguration value object containing all agent config
            llm_service: LangGraph LLM service for this agent
            toolset_service: Optional LangGraph toolset service
            metadata: Static metadata about the agent (id, name, template_id, etc.)
        """
        metadata = metadata or {}
        
        # Initialize identity and template fields from metadata (from BaseAgentTemplate)
        self.id = metadata.get("agent_id", "unknown")
        self.name = metadata.get("agent_name", "Unknown Agent")
        self.template_id = metadata.get("template_id", self.template_id)
        self.template_version = metadata.get("template_version", self.template_version)
        
        # Store the configuration value object
        self.agent_configuration = configuration
        
        # Get template configuration dict for backward compatibility
        self.template_config = configuration.get_template_configuration()
        self.system_prompt = configuration.system_prompt

        # LangGraph-specific initialization
        self.llm_service = llm_service
        self.toolset_service = toolset_service

        self.llm_config_id = configuration.llm_config_id
        self.default_temperature = configuration.get_temperature()
        self.default_max_tokens = configuration.get_max_tokens()
        self.toolset_configs = configuration.get_toolset_names()

        self.llm_client = self._get_llm_client()
        self.toolset_client = self._get_toolset_client()

    def _get_llm_client(self, temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        """Get LLM client configured with execution parameters."""
        execution_params = {}
        
        # Use effective parameters (template defaults vs execution overrides)
        effective_temperature = temperature if temperature is not None else self.default_temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if effective_temperature is not None:
            execution_params["temperature"] = effective_temperature
        if effective_max_tokens is not None:
            execution_params["max_tokens"] = effective_max_tokens
            
        return self.llm_service.get_client(self.llm_config_id, **execution_params)

    def _get_toolset_client(self):
        """Get toolset client for this agent."""
        if self.toolset_service and self.toolset_configs:
            return self.toolset_service.create_client(self.toolset_configs)
        return None

    @abstractmethod
    async def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph execution graph. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _create_initial_state(self, messages: list[ChatMessage]) -> Any:
        """Create the initial state for LangGraph execution.
        
        Each template defines its own state structure.
        Args:
            messages: Input messages to convert to the template's state format
        Returns:
            State object appropriate for this template's graph
        """
        pass

    @abstractmethod
    async def _extract_final_content(self, final_state: Any) -> str:
        """Extract the final response content from the execution state.
        
        Args:
            final_state: The final state returned by LangGraph execution
        Returns:
            The response content as a string
        """
        pass
    
    @abstractmethod
    async def _process_stream_chunk(
        self, 
        chunk: BaseMessageChunk | Any, 
        chunk_index: int = 0,
        metadata: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Process a streaming chunk from LangGraph execution.
        
        Args:
            chunk: Raw chunk from LangGraph streaming
            chunk_index: Index of this chunk in the sequence
            metadata: Optional metadata associated with the chunk
        Yields:
            StreamingChunk objects for intermediate streaming responses
        """
        content = chunk.content if hasattr(chunk, 'content') else chunk
        metadata = metadata or {}

        yield StreamingChunk(
            content=str(content),
            finish_reason=None,
            metadata={
                'template_id': self.template_id,
                'framework': 'langgraph',
                'chunk_index': chunk_index,
                **metadata
            }
        )

    async def get_graph(self) -> CompiledStateGraph:
        """Get the LangGraph execution graph."""
        if not hasattr(self, '_graph') or self._graph is None:
            self._graph = await self._build_graph()
        return self._graph

    def _convert_to_langgraph_messages(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert ChatMessage format to LangGraph BaseMessage format."""
        langgraph_messages = []
        
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                langgraph_messages.append(SystemMessage(content=message.content))
            elif message.role == MessageRole.USER:
                langgraph_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langgraph_messages.append(AIMessage(content=message.content))
            else:
                langgraph_messages.append(HumanMessage(content=message.content))
        
        return langgraph_messages

    def _convert_from_langgraph_message(self, message: BaseMessage) -> ChatMessage:
        """Convert LangGraph's BaseMessage format to our ChatMessage format."""
        if isinstance(message, SystemMessage):
            role = MessageRole.SYSTEM
        elif isinstance(message, HumanMessage):
            role = MessageRole.USER
        elif isinstance(message, AIMessage):
            role = MessageRole.ASSISTANT
        else:
            role = MessageRole.ASSISTANT

        # Handle both string content and list content
        content = message.content
        if isinstance(content, list):
            # Extract text from content list
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        text_parts.append(item["text"])
                    elif "content" in item:
                        text_parts.append(item["content"])
                else:
                    text_parts.append(str(item))
            content = "".join(text_parts)

        return ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(UTC),
            metadata={}
        )

    async def execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Standard execute implementation for LangGraph agents."""
        logger.debug(f"🎯 LangGraph execute: {self.template_id} with {len(messages)} messages")
        logger.debug(f"🔧 Execution params - temp: {temperature}, max_tokens: {max_tokens}")
        
        start_time = time.time()
        
        try:
            # Get the compiled graph
            graph = await self.get_graph()
            
            # Create the initial state using template-specific method
            initial_state = self._create_initial_state(messages)
            
            # Execute the graph
            final_state = await graph.ainvoke(initial_state)
            
            # Extract content using template-specific method
            content = await self._extract_final_content(final_state)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"✅ LangGraph execution completed: {self.template_id} in {processing_time}ms")
            
            return ExecutionResult(
                success=True,
                message=content,
                finish_reason="stop",
                prompt_tokens=0,  # Simplified for now - could be enhanced
                completion_tokens=0,  # Simplified for now - could be enhanced  
                processing_time_ms=processing_time,
                metadata={
                    'template_id': self.template_id,
                    'framework': 'langgraph',
                    **(metadata or {})
                }
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"❌ LangGraph execution failed: {self.template_id} after {processing_time}ms: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time,
                metadata={'template_id': self.template_id, 'framework': 'langgraph'}
            )

    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        stream_mode: Literal["messages"] = "messages",  # support only "messages" for now
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Standard stream execute implementation for LangGraph agents."""
        logger.debug(f"🌊 LangGraph stream execute: {self.template_id} with {len(messages)} messages")
        logger.debug(f"🔧 Stream params - temp: {temperature}, max_tokens: {max_tokens}")
        
        try:
            # Get the compiled graph
            graph = await self.get_graph()
            
            # Create the initial state using template-specific method
            initial_state = self._create_initial_state(messages)
            
            # Stream the graph execution
            chunk_index = 0
            total_content_length = 0
            
            async for chunk in graph.astream(initial_state, stream_mode=stream_mode):
                logger.debug(f"📦 Processing stream chunk #{chunk_index}")
                logger.debug(f"📦 Chunk data #{chunk}")
                # chunk is a tuple of message and metadata
                message, metadata = chunk   # type: ignore
                
                # Let subclasses handle chunk processing for streaming
                # This is template-specific since state structures differ
                chunk_generator = self._process_stream_chunk(message, chunk_index, metadata=metadata)
                
                async for completion_chunk in chunk_generator:
                    content_len = len(getattr(completion_chunk, 'content', ''))
                    total_content_length += content_len
                    
                    logger.debug(f"📝 Processed stream chunk #{chunk_index}: {content_len} chars")
                    logger.debug(f"📝 Processed stream chunk data #{completion_chunk}")
                    chunk_index += 1
                    yield completion_chunk
                
            logger.info(f"🏁 LangGraph streaming completed: {self.template_id}, "
                       f"{chunk_index} chunks, {total_content_length} total chars")
            
            # Final chunk with finish reason  
            yield StreamingChunk(
                content="",
                finish_reason="stop",
                metadata={
                    'template_id': self.template_id,
                    'framework': 'langgraph',
                    'total_chunks': chunk_index,
                    'total_content_length': total_content_length,
                    **(metadata or {})
                }
            )
            
        except Exception as e:
            logger.error(f"❌ LangGraph streaming failed: {self.template_id}: {e}")
            # Yield error chunk
            yield StreamingChunk(
                content="",
                finish_reason="error",
                metadata={
                    'error': str(e),
                    'template_id': self.template_id,
                    'framework': 'langgraph'
                }
            )

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
        return f"BaseLangGraphAgent(id='{self.id}', template_id='{self.template_id}')"

"""LangGraph Base Agent Templates - Framework-specific base classes.

This module provides three base classes for building LangGraph-based agents:

1. BaseLangGraphAgent: Core functionality shared by all LangGraph agents
   - Template metadata and configuration handling
   - Message conversion utilities
   - LLM/toolset client management
   - Non-streaming execution (mode-agnostic)

2. BaseLangGraphChatAgent: For conversational/chat-focused agents
   - Uses 'messages' stream mode for fluent, real-time responses
   - Streams individual message chunks as they're generated
   - Best for interactive chat experiences

3. BaseLangGraphTaskAgent: For task-oriented/workflow agents
   - Uses 'updates' stream mode for state-based updates
   - Streams only significant state changes
   - Best for multi-step workflows where intermediate states should be hidden

Template authors should inherit from either BaseLangGraphChatAgent or 
BaseLangGraphTaskAgent depending on their use case.
"""

from curses import meta
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Generic, Literal, Optional, TypeVar
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

# Type variable for configuration schema
ConfigSchemaType = TypeVar('ConfigSchemaType', bound=BaseModel)


class BaseLangGraphAgent(ABC, Generic[ConfigSchemaType]):
    """
    Core base class for all LangGraph agent templates.

    This abstract class provides the foundation for LangGraph-based agents,
    containing all shared functionality that doesn't depend on the streaming mode.
    
    **DO NOT inherit from this class directly.** Instead, use:
    - `BaseLangGraphChatAgent` for conversational agents
    - `BaseLangGraphTaskAgent` for task-oriented agents
    
    ## Responsibilities:
    
    ### Configuration Management
    - Validates and stores agent configuration
    - Converts configuration to typed Pydantic models
    - Provides configuration introspection methods
    
    ### LLM & Tool Integration
    - Manages LLM client connections with temperature/token settings
    - Integrates toolset services for agent capabilities
    - Handles execution parameter overrides
    
    ### Message Conversion
    - Converts between ChatMessage and LangGraph BaseMessage formats
    - Handles different message roles (system, user, assistant)
    - Supports both string and structured content
    
    ### Graph Management
    - Provides graph building interface
    - Caches compiled graphs for reuse
    - Manages graph lifecycle
    
    ### Non-Streaming Execution
    - Implements standard synchronous execution
    - Returns complete ExecutionResult objects
    - Mode-agnostic (works with any streaming mode)
    
    ## Type Parameters:
        ConfigSchemaType: The Pydantic model type for this agent's configuration schema.
                         Must define all configuration fields with validation rules.
    
    ## Abstract Methods (must be implemented by subclasses):
        _build_graph(): Build the LangGraph execution graph
        _create_initial_state(): Convert messages to graph state
        _extract_final_content(): Extract response from final state
        stream_execute(): Stream execution (implemented by chat/task base classes)
    
    ## Template Metadata (should be overridden in subclasses):
        template_name: Human-readable name
        template_id: Unique identifier (kebab-case)
        template_version: Semantic version string
        template_description: Brief description of capabilities
        framework: Should always be "langgraph"
    
    ## Example:
        ```python
        class MyAgentConfig(BaseModel):
            max_iterations: int = Field(default=5, description="Max reasoning steps")
            
        class MyAgent(BaseLangGraphChatAgent[MyAgentConfig]):
            template_name = "My Conversational Agent"
            template_id = "my-agent"
            config_schema = MyAgentConfig
            
            async def _build_graph(self) -> CompiledStateGraph:
                # Build your graph here
                ...
        ```
    """

    # Template Metadata (should be overridden in subclasses)
    template_name: str = "Base LangGraph Agent Template"
    template_id: str = "base-langgraph-agent"
    template_version: str = "1.0.0"
    template_description: str = "Base LangGraph agent template"
    framework: str = "langgraph"

    # Placeholder for the configuration schema, should be overridden in subclasses
    config_schema: type[ConfigSchemaType]

    def __init__(
        self, 
        configuration: AgentConfiguration, 
        llm_service: LangGraphLLMService, 
        toolset_service: Optional[LangGraphToolsetService] = None, 
        metadata: Optional[dict[str, Any]] = None
    ):
        """Initialize LangGraph agent instance with configuration and services.
        
        This constructor sets up the agent's identity, configuration, and service
        connections. It's called by the framework when instantiating an agent.
        
        Args:
            configuration: AgentConfiguration value object containing:
                - system_prompt: System instructions for the agent
                - llm_config_id: LLM configuration identifier
                - template_configuration: Template-specific settings
                - toolset_configs: Tool configurations
                - execution_params: Default temperature, max_tokens, etc.
                
            llm_service: LangGraph LLM service for creating LLM clients.
                        Handles provider-specific client creation and configuration.
                        
            toolset_service: Optional LangGraph toolset service for tool integration.
                           Provides access to tools and manages tool execution.
                           
            metadata: Static metadata about the agent instance:
                - agent_id: Unique identifier for this agent instance
                - agent_name: Human-readable name
                - template_id: Template this agent was created from
                - template_version: Version of the template
                
        Note:
            Template authors typically don't need to override this method.
            Override `_build_graph()` and other abstract methods instead.
        """
        metadata = metadata or {}
        
        # Initialize identity and template fields from metadata
        self.id = metadata.get("agent_id", "unknown")
        self.name = metadata.get("agent_name", "Unknown Agent")
        self.template_id = metadata.get("template_id", self.template_id)
        self.template_version = metadata.get("template_version", self.template_version)
        
        # Store the configuration value object
        self.agent_configuration = configuration
        
        # Convert template configuration dict to config_schema object
        self.template_config = configuration.get_template_configuration()
        self.config: ConfigSchemaType = self.config_schema.model_validate(self.template_config)
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
        """Get LLM client configured with execution parameters.
        
        Creates a new LLM client instance with the specified temperature and token limits.
        If parameters are not provided, uses the agent's default values.
        
        Args:
            temperature: Optional temperature override for this client
            max_tokens: Optional max tokens override for this client
            
        Returns:
            Configured LLM client instance ready for use
        """
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
        """Get toolset client for this agent.
        
        Creates a toolset client with all configured tools available.
        
        Returns:
            Toolset client instance or None if no tools configured
        """
        if self.toolset_service and self.toolset_configs:
            return self.toolset_service.create_client(self.toolset_configs)
        return None

    @abstractmethod
    async def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph execution graph.
        
        This method must be implemented by template authors to define the agent's
        execution flow. The graph defines nodes (functions), edges (transitions),
        and conditional routing logic.
        
        Returns:
            CompiledStateGraph: The compiled LangGraph ready for execution
            
        Example:
            ```python
            async def _build_graph(self) -> CompiledStateGraph:
                workflow = StateGraph(AgentState)
                workflow.add_node("agent", self._agent_step)
                workflow.add_node("tools", self._tool_step)
                workflow.set_entry_point("agent")
                workflow.add_conditional_edges("agent", self._should_continue)
                workflow.add_edge("tools", "agent")
                return workflow.compile()
            ```
        """
        pass

    @abstractmethod
    def _create_initial_state(self, messages: list[ChatMessage]) -> Any:
        """Create the initial state for LangGraph execution.
        
        Converts the input messages into the state format expected by your graph.
        Each template defines its own state structure based on its needs.
        
        Args:
            messages: Input messages in ChatMessage format (from the API)
            
        Returns:
            State object appropriate for this template's graph. The structure
            depends on your StateGraph definition.
            
        Example:
            ```python
            def _create_initial_state(self, messages: list[ChatMessage]) -> dict:
                return {
                    "messages": self._convert_to_langgraph_messages(messages),
                    "iteration": 0,
                    "max_iterations": self.config.max_iterations
                }
            ```
        """
        pass

    @abstractmethod
    async def _extract_final_content(self, final_state: Any) -> str:
        """Extract the final response content from the execution state.
        
        After graph execution completes, this method extracts the response text
        that should be returned to the user.
        
        Args:
            final_state: The final state returned by LangGraph execution.
                        Structure matches your graph's state definition.
            
        Returns:
            The response content as a string
            
        Example:
            ```python
            async def _extract_final_content(self, final_state: dict) -> str:
                messages = final_state.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    return last_message.content
                return ""
            ```
        """
        pass

    async def get_graph(self) -> CompiledStateGraph:
        """Get the LangGraph execution graph.
        
        Lazily builds and caches the graph on first access. Subsequent calls
        return the cached graph instance.
        
        Returns:
            The compiled LangGraph execution graph
        """
        if not hasattr(self, '_graph') or self._graph is None:
            self._graph = await self._build_graph()
        return self._graph

    def _convert_to_langgraph_messages(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert ChatMessage format to LangGraph BaseMessage format.
        
        Transforms our domain ChatMessage objects into LangChain's BaseMessage
        format that LangGraph expects.
        
        Args:
            messages: List of ChatMessage objects from the API
            
        Returns:
            List of BaseMessage objects (SystemMessage, HumanMessage, AIMessage)
        """
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
        """Convert LangGraph's BaseMessage format to our ChatMessage format.
        
        Transforms LangChain's BaseMessage objects back into our domain ChatMessage
        format. Handles both string and structured content.
        
        Args:
            message: BaseMessage from LangGraph (SystemMessage, HumanMessage, AIMessage)
            
        Returns:
            ChatMessage object in our domain format
        """
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
        """Execute the agent synchronously without streaming.
        
        This method runs the graph to completion and returns the final result.
        It's mode-agnostic and works the same for both chat and task agents.
        
        Args:
            messages: Input messages from the user
            temperature: Optional temperature override for this execution
            max_tokens: Optional max tokens override for this execution
            metadata: Optional metadata to include in the result
            
        Returns:
            ExecutionResult with the complete response
            
        Note:
            Template authors typically don't need to override this method.
            Override the abstract methods (_build_graph, _create_initial_state,
            _extract_final_content) to customize the execution behavior.
        """
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
            logger.exception(f"Full exception details for {self.template_id}:")
            return ExecutionResult(
                success=False,
                error=str(e) if str(e) else f"{type(e).__name__}: {repr(e)}",
                processing_time_ms=processing_time,
                metadata={'template_id': self.template_id, 'framework': 'langgraph'}
            )

    @abstractmethod
    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Execute the agent with streaming responses.
        
        This abstract method must be implemented by the specialized base classes
        (BaseLangGraphChatAgent or BaseLangGraphTaskAgent) to handle their
        specific streaming modes.
        
        Args:
            messages: Input messages from the user
            temperature: Optional temperature override for this execution
            max_tokens: Optional max tokens override for this execution
            metadata: Optional metadata to include in chunks
            
        Yields:
            StreamingChunk objects containing incremental responses
            
        Note:
            Template authors should NOT override this method directly.
            Instead, override the mode-specific processing methods:
            - `_process_message_chunk()` for chat agents
            - `_process_state_update()` for task agents
        """
        pass

    @classmethod
    def get_config_fields(cls) -> list[ConfigField]:
        """Get the configuration fields for the template as domain objects."""
        # Get the standard Pydantic JSON schema
        pydantic_schema = cls.config_schema.model_json_schema()
        
        # Helper to recursively convert JSON schema field to ConfigField
        def convert_field(field_key: str, field_info: dict, parent_schema: dict) -> ConfigField:
            """Convert a JSON schema field definition to ConfigField, handling nested types."""
            # Handle anyOf (e.g., Optional types that generate {"anyOf": [{"type": "array"}, {"type": "null"}]})
            if "anyOf" in field_info:
                # Find the non-null option
                for option in field_info["anyOf"]:
                    if option.get("type") != "null":
                        # Use the non-null option as the field_info
                        field_info = {**field_info, **option}
                        # Remove anyOf now that we've resolved it
                        field_info.pop("anyOf", None)
                        break
            
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
            
            # Handle nested types
            items = None
            properties = None
            
            if field_type == "array":
                # Handle array items (nested schema)
                items_schema = field_info.get("items")
                if items_schema and isinstance(items_schema, dict):
                    # Recursively convert items schema
                    # Use a placeholder key for the items field. The parent schema
                    # for an item is the array schema itself (`field_info`).
                    items = convert_field("items", items_schema, field_info)
            
            elif field_type == "object":
                # Handle object properties (nested schemas)
                properties_schema = field_info.get("properties")
                if properties_schema and isinstance(properties_schema, dict):
                    # Recursively convert each property
                    properties = {}
                    for prop_key, prop_schema in properties_schema.items():
                        properties[prop_key] = convert_field(prop_key, prop_schema, field_info)
            
            # Handle $ref definitions (resolve from definitions in schema)
            if "$ref" in field_info:
                ref_path = field_info["$ref"]
                # Extract definition name from #/$defs/DefinitionName
                if ref_path.startswith("#/$defs/") or ref_path.startswith("#/definitions/"):
                    def_name = ref_path.split("/")[-1]
                    definitions = pydantic_schema.get("$defs") or pydantic_schema.get("definitions", {})
                    if def_name in definitions:
                        # Recursively process the referenced definition
                        # Pass the original parent_schema so the optional flag is checked correctly
                        # against the parent's required list, not the referenced definition's.
                        ref_schema = definitions[def_name]
                        return convert_field(field_key, ref_schema, parent_schema)
            
            # The 'optional' flag is only relevant for properties of an object.
            # For the item schema of an array (keyed as "items"), the concept of being
            # optional is not meaningful, so we default it to False.
            # We check if the parent's type is 'array' to correctly identify an item schema.
            is_optional = (
                field_key not in parent_schema.get("required", [])
                if not (field_key == "items" and parent_schema.get("type") == "array")
                else False
            )

            # Create ConfigField domain object
            config_field = ConfigField(
                key=field_key,
                field_type=field_type,
                description=field_info.get("description"),
                default_value=field_info.get("default"),
                validation=validation,
                optional=is_optional,
                items=items,
                properties=properties
            )
            
            return config_field
        
        # Convert top-level properties to ConfigField domain objects
        config_fields = []
        properties = pydantic_schema.get("properties", {})
        
        for field_key, field_info in properties.items():
            config_field = convert_field(field_key, field_info, pydantic_schema)
            config_fields.append(config_field)
        
        return config_fields

    @classmethod
    def validate_configuration(cls, configuration: dict[str, Any]) -> tuple[bool, Optional[ValidationError]]:
        """Validate the configuration for the template."""
        try:
            logger.debug(f"Validating configuration for template '{cls.config_schema}' with data: {configuration}")
            cls.config_schema.model_validate(configuration)
            return True, None
        except ValidationError as e:
            return False, e
        
    def get_config(self) -> BaseModel:
        """Get the configuration as a Pydantic model instance."""
        return self.config
    
    def cleanup(self):
        """Clean up agent resources if needed."""
        pass

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.template_name} ({self.id})"

    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return f"BaseLangGraphAgent(id='{self.id}', template_id='{self.template_id}')"


class BaseLangGraphChatAgent(BaseLangGraphAgent[ConfigSchemaType]):
    """
    Base class for chat-focused LangGraph agents using 'messages' stream mode.
    
    This class is designed for conversational agents where you want to stream
    the response as it's being generated, similar to ChatGPT's typing effect.
    
    ## When to Use This Class:
    
    ✅ **Use BaseLangGraphChatAgent for:**
    - Conversational chatbots
    - Interactive Q&A agents
    - Agents where showing partial responses improves UX
    - Agents where tool calls should be visible to users
    - ReAct-style agents with visible reasoning
    
    ❌ **Don't use BaseLangGraphChatAgent for:**
    - Multi-step workflows with internal states
    - Agents where you want to hide intermediate thinking
    - Task automation agents with complex state machines
    
    ## Streaming Behavior:
    
    This class uses LangGraph's `"messages"` stream mode, which yields:
    - Individual message chunks as they're generated by the LLM
    - Real-time streaming of partial responses
    - Fine-grained control over what's displayed
    
    ## Methods to Implement:
    
    ### Required (from BaseLangGraphAgent):
    - `_build_graph()`: Build your LangGraph execution graph
    - `_create_initial_state()`: Convert messages to graph state
    - `_extract_final_content()`: Extract final response from state
    
    ### Optional Override:
    - `_process_message_chunk()`: Customize how message chunks are processed
    
    ## Example Implementation:
    
    ```python
    from pydantic import BaseModel, Field
    from langgraph.graph import StateGraph
    
    class MyAgentConfig(BaseModel):
        \"\"\"Configuration for my chat agent.\"\"\"
        temperature: float = Field(default=0.7, description="LLM temperature")
        max_iterations: int = Field(default=5, description="Max tool iterations")
    
    class MyChatAgent(BaseLangGraphChatAgent[MyAgentConfig]):
        \"\"\"A simple conversational agent.\"\"\"
        
        template_name = "My Chat Agent"
        template_id = "my-chat-agent"
        template_version = "1.0.0"
        template_description = "A friendly conversational assistant"
        config_schema = MyAgentConfig
        
        async def _build_graph(self) -> CompiledStateGraph:
            # Define your graph structure
            workflow = StateGraph(AgentState)
            workflow.add_node("chat", self._chat_node)
            workflow.set_entry_point("chat")
            workflow.set_finish_point("chat")
            return workflow.compile()
        
        def _create_initial_state(self, messages):
            return {
                "messages": self._convert_to_langgraph_messages(messages),
            }
        
        async def _extract_final_content(self, final_state):
            messages = final_state.get("messages", [])
            return messages[-1].content if messages else ""
    ```
    
    ## Customizing Chunk Processing:
    
    ```python
    class MyChatAgent(BaseLangGraphChatAgent[MyAgentConfig]):
        # ...
        
        async def _process_message_chunk(self, message, chunk_index, metadata):
            # Add custom logic for filtering or transforming chunks
            if hasattr(message, 'content') and message.content:
                # Only yield non-empty content
                yield StreamingChunk(
                    content=message.content,
                    finish_reason=None,
                    metadata={
                        'chunk_index': chunk_index,
                        'message_type': type(message).__name__,
                        **metadata
                    }
                )
    ```
    """

    async def _process_message_chunk(
        self, 
        message: BaseMessageChunk,
        chunk_index: int = 0,
        metadata: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Process a message chunk from 'messages' stream mode.
        
        This method is called for each chunk received from LangGraph when using
        the 'messages' stream mode. By default, it extracts the content and
        yields it as a StreamingChunk.
        
        Template authors can override this method to:
        - Filter out certain types of messages
        - Transform message content before streaming
        - Add custom metadata to chunks
        - Implement special handling for tool calls
        
        Args:
            message: BaseMessageChunk from LangGraph containing partial content
            chunk_index: Sequential index of this chunk in the stream
            metadata: Additional metadata associated with this message chunk
            
        Yields:
            StreamingChunk objects containing the processed content
            
        Example Override:
            ```python
            async def _process_message_chunk(self, message, chunk_index, metadata):
                # Skip system messages in streaming
                if isinstance(message, SystemMessage):
                    return
                
                content = message.content if hasattr(message, 'content') else str(message)
                
                # Add thinking indicator for tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    yield StreamingChunk(
                        content=f"[Using tool: {message.tool_calls[0]['name']}]\\n",
                        finish_reason=None,
                        metadata={'chunk_index': chunk_index, 'type': 'tool_call'}
                    )
                
                # Yield the actual content
                if content:
                    yield StreamingChunk(
                        content=content,
                        finish_reason=None,
                        metadata={'chunk_index': chunk_index}
                    )
            ```
        """
        # Extract content from the message
        content = message.content if hasattr(message, 'content') else str(message)
        
        # Handle list content (convert to string)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        text_parts.append(str(item["text"]))
                    elif "content" in item:
                        text_parts.append(str(item["content"]))
                else:
                    text_parts.append(str(item))
            content = "".join(text_parts)
        else:
            content = str(content)
        
        yield StreamingChunk(
            content=content,
            finish_reason=None,
            metadata={
                'template_id': self.template_id,
                'framework': 'langgraph',
                'stream_mode': 'messages',
                'chunk_index': chunk_index,
                **(metadata or {})
            }
        )

    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Execute the chat agent with streaming responses using 'messages' mode.
        
        This implementation streams individual message chunks as they're generated,
        providing real-time feedback to users. Each chunk from the LLM is processed
        and yielded as soon as it's available.
        
        Args:
            messages: Input messages from the user
            temperature: Optional temperature override for this execution
            max_tokens: Optional max tokens override for this execution
            metadata: Optional metadata to include in chunks
            
        Yields:
            StreamingChunk objects containing incremental message content
            
        Note:
            Template authors should NOT override this method. Instead, override
            `_process_message_chunk()` to customize chunk processing behavior.
        """
        logger.debug(f"🌊 LangGraph chat stream execute: {self.template_id} with {len(messages)} messages")
        logger.debug(f"🔧 Stream params - temp: {temperature}, max_tokens: {max_tokens}")
        
        try:
            # Get the compiled graph
            graph = await self.get_graph()
            
            # Create the initial state using template-specific method
            initial_state = self._create_initial_state(messages)
            
            # Stream with 'messages' mode
            chunk_index = 0
            total_content_length = 0
            
            async for chunk_data in graph.astream(
                initial_state, 
                stream_mode="messages"
            ):
                logger.debug(f"📦 Processing message chunk #{chunk_index}")
                
                # Unpack the message and metadata tuple from LangGraph
                message, msg_metadata = chunk_data  # type: ignore
                
                # Process through template-specific handler
                async for completion_chunk in self._process_message_chunk(
                    message, chunk_index, metadata=msg_metadata  # type: ignore
                ):
                    content_len = len(completion_chunk.content)
                    total_content_length += content_len
                    
                    logger.debug(f"📝 Processed message chunk #{chunk_index}: {content_len} chars")
                    chunk_index += 1
                    yield completion_chunk
            
            logger.info(f"🏁 Chat streaming completed: {self.template_id}, "
                       f"{chunk_index} chunks, {total_content_length} total chars")
            
            # Final chunk with finish reason
            yield StreamingChunk(
                content="",
                finish_reason="stop",
                metadata={
                    'template_id': self.template_id,
                    'framework': 'langgraph',
                    'stream_mode': 'messages',
                    'total_chunks': chunk_index,
                    'total_content_length': total_content_length,
                    **(metadata or {})
                }
            )
            
        except Exception as e:
            logger.exception(f"❌ Chat streaming failed: {self.template_id}: {e}")
            yield StreamingChunk(
                content="",
                finish_reason="error",
                metadata={
                    'error': str(e),
                    'template_id': self.template_id,
                    'framework': 'langgraph',
                    'stream_mode': 'messages'
                }
            )


class BaseLangGraphTaskAgent(BaseLangGraphAgent[ConfigSchemaType]):
    """
    Base class for task-focused LangGraph agents using 'updates' stream mode.
    
    This class is designed for task-oriented agents where you want to stream
    only significant state changes, hiding the internal reasoning and intermediate
    steps from the user.
    
    ## When to Use This Class:
    
    ✅ **Use BaseLangGraphTaskAgent for:**
    - Multi-step workflow agents
    - Task automation agents
    - Agents with complex internal state machines
    - Agents where you want to hide intermediate reasoning
    - Planning and execution agents with multiple phases
    - Agents that should only show final or milestone results
    
    ❌ **Don't use BaseLangGraphTaskAgent for:**
    - Simple conversational chatbots
    - Agents where users expect real-time typing effects
    - Agents where all intermediate steps should be visible
    
    ## Streaming Behavior:
    
    This class uses LangGraph's `"updates"` stream mode, which yields:
    - Complete state updates after each node execution
    - Only significant state changes (not every token)
    - Full control over what gets streamed to users
    
    ## Methods to Implement:
    
    ### Required (from BaseLangGraphAgent):
    - `_build_graph()`: Build your LangGraph execution graph
    - `_create_initial_state()`: Convert messages to graph state
    - `_extract_final_content()`: Extract final response from state
    
    ### Required (TaskAgent-specific):
    - `_process_state_update()`: Process state updates and decide what to stream
    
    ## Example Implementation:
    
    ```python
    from pydantic import BaseModel, Field
    from langgraph.graph import StateGraph
    
    class WorkflowConfig(BaseModel):
        \"\"\"Configuration for workflow agent.\"\"\"
        max_planning_steps: int = Field(default=3, description="Max planning iterations")
        enable_validation: bool = Field(default=True, description="Validate results")
    
    class WorkflowAgent(BaseLangGraphTaskAgent[WorkflowConfig]):
        \"\"\"A multi-step workflow agent.\"\"\"
        
        template_name = "Workflow Agent"
        template_id = "workflow-agent"
        template_version = "1.0.0"
        template_description = "Executes multi-step workflows"
        config_schema = WorkflowConfig
        
        async def _build_graph(self) -> CompiledStateGraph:
            workflow = StateGraph(WorkflowState)
            workflow.add_node("plan", self._plan_node)
            workflow.add_node("execute", self._execute_node)
            workflow.add_node("validate", self._validate_node)
            workflow.set_entry_point("plan")
            workflow.add_edge("plan", "execute")
            workflow.add_conditional_edges("execute", self._should_validate)
            return workflow.compile()
        
        def _create_initial_state(self, messages):
            return {
                "messages": self._convert_to_langgraph_messages(messages),
                "plan": None,
                "results": [],
                "phase": "planning"
            }
        
        async def _extract_final_content(self, final_state):
            return final_state.get("final_result", "")
        
        async def _process_state_update(self, state_update, chunk_index, metadata):
            # Only stream updates from significant nodes
            for node_name, node_output in state_update.items():
                if node_name == "plan":
                    plan = node_output.get("plan", "")
                    if plan:
                        yield StreamingChunk(
                            content=f"📋 Plan: {plan}\\n",
                            finish_reason=None,
                            metadata={'phase': 'planning', 'chunk_index': chunk_index}
                        )
                elif node_name == "execute":
                    result = node_output.get("result", "")
                    if result:
                        yield StreamingChunk(
                            content=f"✓ Executed: {result}\\n",
                            finish_reason=None,
                            metadata={'phase': 'execution', 'chunk_index': chunk_index}
                        )
    ```
    
    ## State Update Processing:
    
    The `_process_state_update()` method receives state updates as dictionaries
    where keys are node names and values are the outputs from those nodes:
    
    ```python
    state_update = {
        "node_name": {
            "field1": "value1",
            "field2": "value2"
        }
    }
    ```
    
    You have full control over:
    - Which nodes trigger streaming output
    - What content is extracted from state updates
    - How content is formatted for users
    - Which intermediate steps are hidden
    """

    @abstractmethod
    async def _process_state_update(
        self,
        state_update: dict[str, Any],
        chunk_index: int = 0,
        metadata: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Process a state update from 'updates' stream mode.
        
        This method MUST be implemented by template authors to handle state updates
        from their graph execution. It's called after each node executes, giving you
        full control over what gets streamed to users.
        
        State updates are dictionaries where:
        - Keys are node names that just executed
        - Values are the output state from those nodes
        
        Template authors should:
        1. Check which nodes updated
        2. Extract relevant information from the updates
        3. Decide whether to yield streaming chunks
        4. Format content appropriately for users
        
        Args:
            state_update: Dictionary of node updates from LangGraph
                         Format: {node_name: node_output_state}
            chunk_index: Sequential index of this update in the stream
            metadata: Additional metadata for this update
            
        Yields:
            StreamingChunk objects for significant state changes
            
        Example Implementation:
            ```python
            async def _process_state_update(self, state_update, chunk_index, metadata):
                # Process updates from specific nodes
                for node_name, node_state in state_update.items():
                    if node_name == "research":
                        # Stream research findings
                        findings = node_state.get("findings", [])
                        if findings:
                            content = f"Found {len(findings)} relevant sources\\n"
                            yield StreamingChunk(
                                content=content,
                                finish_reason=None,
                                metadata={'node': node_name, 'chunk_index': chunk_index}
                            )
                    
                    elif node_name == "analyze":
                        # Stream analysis results
                        analysis = node_state.get("analysis", "")
                        if analysis:
                            yield StreamingChunk(
                                content=f"Analysis: {analysis}\\n",
                                finish_reason=None,
                                metadata={'node': node_name, 'chunk_index': chunk_index}
                            )
                    
                    # Skip internal nodes like "routing" or "validation"
                    # by simply not yielding anything for them
            ```
        
        Note:
            Return without yielding (or use `return` with no yield) to skip
            streaming for certain state updates. This is useful for hiding
            internal processing steps.
        """
        pass

    async def stream_execute(
        self,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Execute the task agent with streaming responses using 'updates' mode.
        
        This implementation streams state updates as nodes complete execution,
        allowing fine-grained control over what users see. Only significant
        state changes (as determined by `_process_state_update()`) are streamed.
        
        Args:
            messages: Input messages from the user
            temperature: Optional temperature override for this execution
            max_tokens: Optional max tokens override for this execution
            metadata: Optional metadata to include in chunks
            
        Yields:
            StreamingChunk objects containing significant state changes
            
        Note:
            Template authors should NOT override this method. Instead, override
            `_process_state_update()` to customize which state changes are streamed.
        """
        logger.debug(f"🌊 LangGraph task stream execute: {self.template_id} with {len(messages)} messages")
        logger.debug(f"🔧 Stream params - temp: {temperature}, max_tokens: {max_tokens}")
        
        try:
            # Get the compiled graph
            graph = await self.get_graph()
            
            # Create the initial state using template-specific method
            initial_state = self._create_initial_state(messages)
            
            # Stream with 'updates' mode
            update_index = 0
            total_content_length = 0
            
            async for state_update in graph.astream(
                initial_state,
                stream_mode="updates"
            ):
                logger.debug(f"📦 Processing state update #{update_index}")
                logger.debug(f"📊 State update keys: {list(state_update.keys()) if isinstance(state_update, dict) else 'non-dict'}")
                
                # Process through template-specific handler
                async for completion_chunk in self._process_state_update(
                    state_update, update_index, metadata=metadata
                ):
                    content_len = len(completion_chunk.content)
                    total_content_length += content_len
                    
                    logger.debug(f"📝 Processed state update #{update_index}: {content_len} chars")
                    update_index += 1
                    yield completion_chunk
            
            logger.info(f"🏁 Task streaming completed: {self.template_id}, "
                       f"{update_index} updates, {total_content_length} total chars")
            
            # Final chunk with finish reason
            yield StreamingChunk(
                content="",
                finish_reason="stop",
                metadata={
                    'template_id': self.template_id,
                    'framework': 'langgraph',
                    'stream_mode': 'updates',
                    'total_updates': update_index,
                    'total_content_length': total_content_length,
                    **(metadata or {})
                }
            )
            
        except Exception as e:
            logger.exception(f"❌ Task streaming failed: {self.template_id}: {e}")
            yield StreamingChunk(
                content="",
                finish_reason="error",
                metadata={
                    'error': str(e),
                    'template_id': self.template_id,
                    'framework': 'langgraph',
                    'stream_mode': 'updates'
                }
            )

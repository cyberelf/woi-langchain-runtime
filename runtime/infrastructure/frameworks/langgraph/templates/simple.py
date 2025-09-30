"""Simple Test Agent Template - No external dependencies."""

from collections.abc import AsyncGenerator
from typing import Any, Optional

from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
from runtime.core.executors import StreamingChunk
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.domain.value_objects.chat_message import ChatMessage
from .base import BaseLangGraphAgent


class SimpleTestAgentConfig(BaseModel):
    """Configuration for Simple Test Agent."""

    response_prefix: str = Field(
        default="Test: ", description="Prefix for test responses", min_length=1, max_length=50
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.", description="System prompt for the agent"
    )


class SimpleTestAgent(BaseLangGraphAgent):
    """Simple test agent template for validation - no external dependencies."""

    # Template metadata (class variables)
    template_name: str = "Simple Test Agent"
    template_id: str = "langgraph-simple-test"
    template_version: str = "1.0.0"
    template_description: str = "Simple test agent for system validation"
    framework: str = "langgraph"

    # Configuration schema (class variables)
    config_schema: type[BaseModel] = SimpleTestAgentConfig

    def __init__(
        self, 
        configuration: AgentConfiguration, 
        llm_service: LangGraphLLMService, 
        toolset_service: Optional[LangGraphToolsetService] = None,
        metadata: Optional[dict[str, Any]] = None, 
    ):
        """Initialize the simple test agent."""
        super().__init__(configuration, llm_service, toolset_service, metadata)
        self._graph: CompiledStateGraph | None = None
        
        # Extract template-specific configuration using helper methods
        self.response_prefix = self.get_config_value("response_prefix", "Test: ")
        
        # Extract configuration values for LangGraph-specific setup
        self.system_prompt = self.system_prompt or "You are a helpful assistant."

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

    async def _build_graph(self):
        """Build the execution graph for simple test agent."""
        # Simple test agent doesn't need a complex graph
        # Return None for simplicity
        toolset_client = self.toolset_client
        if toolset_client is None:
            tools = []
        else:
            tools = await toolset_client.tools
        
        # Use parameter-aware client to ensure the LLM is configured with 
        # the agent's default temperature and max_tokens
        llm_client = self.llm_client
        
        return create_react_agent(
            model=llm_client,  # type: ignore - LLMClient is actually a BaseChatModel at runtime
            tools=tools,
            prompt=self.system_prompt
        )

    def _create_initial_state(self, messages: list[ChatMessage]) -> dict[str, Any]:
        """Create initial state for simple agent (standard message format)."""
        return {
            "messages": self._convert_to_langgraph_messages(messages)
        }

    async def _extract_final_content(self, final_state: dict[str, Any]) -> str:
        """Extract content from simple agent result with response prefix."""
        # Get the final messages from the graph result
        final_messages = final_state.get("messages", [])
        if not final_messages:
            raise RuntimeError("No messages returned from LangGraph execution")
        
        # Get the last message (should be the assistant's response)
        last_message = final_messages[-1]
        
        # Convert back to our format
        response_message = self._convert_from_langgraph_message(last_message)
        content = response_message.content
        
        # Add response prefix if configured
        if self.response_prefix and not content.startswith(self.response_prefix):
            content = self.response_prefix + content
            
        return content

    async def _process_stream_chunk(
        self,
        chunk: Any,
        chunk_index: int = 0
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Process streaming chunks for simple agent."""


        # Process each chunk from LangGraph
        if isinstance(chunk, dict):
            # Look for message updates in the chunk
            messages_update = chunk.get("messages", [])

            if messages_update:
                # Get the latest message
                latest_message = messages_update[-1]

                if hasattr(latest_message, 'content'):
                    current_content = latest_message.content
                else:
                    current_content = str(latest_message)

                # Add prefix if this is the first chunk and prefix is configured
                if self.response_prefix and not current_content.startswith(self.response_prefix):
                    current_content = self.response_prefix + current_content

                # Yield the content as a streaming chunk (simplified core format)
                yield StreamingChunk(
                    content=current_content,
                    finish_reason=None,
                    metadata={
                        'template_id': self.template_id,
                        'framework': 'langgraph',
                        'chunk_index': chunk_index
                    }
                )
        else:
            # Handle non-dict chunks (strings, etc.)
            content = str(chunk)

            if self.response_prefix and not content.startswith(self.response_prefix):
                content = self.response_prefix + content

            yield StreamingChunk(
                content=content,
                finish_reason=None,
                metadata={
                    'template_id': self.template_id,
                    'framework': 'langgraph',
                    'chunk_index': chunk_index
                }
            )


    

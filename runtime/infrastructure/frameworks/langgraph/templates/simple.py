"""Simple Test Agent Template - No external dependencies."""

from typing import Any, Optional

from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.domain.value_objects.chat_message import ChatMessage
from .base import BaseLangGraphChatAgent


class SimpleTestAgentConfig(BaseModel):
    """Configuration for Simple Test Agent."""

    response_prefix: str = Field(
        default="Test: ", description="Prefix for test responses", min_length=1, max_length=50
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.", description="System prompt for the agent"
    )


class SimpleTestAgent(BaseLangGraphChatAgent[SimpleTestAgentConfig]):
    """Simple test agent template for validation - no external dependencies."""

    # Template metadata (class variables)
    template_name: str = "Simple Test Agent"
    template_id: str = "simple-test"
    template_version: str = "1.0.0"
    template_description: str = "Simple test agent for system validation"
    framework: str = "langgraph"

    # Configuration schema (class variables)
    config_schema: type[SimpleTestAgentConfig] = SimpleTestAgentConfig

    def __init__(
        self, 
        configuration: AgentConfiguration, 
        llm_service: LangGraphLLMService, 
        toolset_service: Optional[LangGraphToolsetService] = None,
        metadata: Optional[dict[str, Any]] = None, 
    ):
        """Initialize the simple test agent."""
        super().__init__(configuration, llm_service, toolset_service, metadata)
        
        # Access configuration via the typed config object - no cast needed!
        self.response_prefix = self.config.response_prefix
        
        # Extract configuration values for LangGraph-specific setup
        self.system_prompt = self.system_prompt or self.config.system_prompt

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
            model=llm_client, 
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

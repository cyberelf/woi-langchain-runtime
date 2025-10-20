"""Test agent plugin for E2E testing.

This agent is used in integration tests to verify the plugin system works correctly.
It demonstrates file and web operations using plugin tools.
"""

from pydantic import BaseModel
from runtime.infrastructure.frameworks.langgraph import llm
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphChatAgent
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from typing import Literal

class NoConfig(BaseModel):
    """No configuration needed for this test agent."""
    pass

class TestPluginAgent(BaseLangGraphChatAgent):
    """Test agent that uses file and web tools from plugins.
    
    This agent is designed for testing:
    - Plugin tool discovery and loading
    - Tool execution in agent workflow
    - File operations (read, write, search)
    - Web operations (fetch, parse)
    """
    
    template_id = "test-plugin-agent"
    template_name = "Test Plugin Agent"
    template_version = "1.0.0"
    template_description = "Agent for testing plugin tools (file and web operations)"

    config_schema = NoConfig

    __version__ = "1.0.0"
    
    def _create_initial_state(self, messages):
        """Create initial state from input messages.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            dict: State with converted messages
        """
        return {
            "messages": self._convert_to_langgraph_messages(messages),
        }
    
    async def _extract_final_content(self, final_state):
        """Extract final response content from state.
        
        Args:
            final_state: Final state from graph execution
            
        Returns:
            str: Response content
        """
        messages = final_state.get("messages", [])
        if messages:
            last_message = messages[-1]
            return last_message.content if hasattr(last_message, 'content') else str(last_message)
        return ""
    
    async def _build_graph(self):
        """Build the agent's conversation graph.
        
        This agent supports tool calling and returns structured responses.
        
        Returns:
            Compiled StateGraph
        """
        # Get tools
        tools = await self.toolset_client.tools if self.toolset_client else []
        
        if tools:
            # Bind tools to LLM
            llm = self.llm_client.bind_tools(tools)
        else:
            llm = self.llm_client
        
        # Define the agent node function
        def call_model(state: MessagesState):
            """Call the LLM with the current messages."""
            messages = state["messages"]
            response = llm.invoke(messages)
            return {"messages": [response]}
        
        # Create state graph
        graph = StateGraph(MessagesState)
        
        # Add nodes
        graph.add_node("agent", call_model)
        graph.add_node("tools", ToolNode(tools))
        
        # Add edges
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "end": END,
            }
        )
        graph.add_edge("tools", "agent")

        # Set entry point
        graph.set_entry_point("agent")
        
        # Compile and return
        return graph.compile()
    
    def _should_continue(self, state: MessagesState) -> Literal["tools", "end"]:
        """Determine if we should continue to tools or end.
        
        Args:
            state: Current conversation state
            
        Returns:
            Next node to visit
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, continue to tools
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        
        # Otherwise end
        return "end"

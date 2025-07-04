"""Base Agent Template - Enhanced Agent with Template Metadata."""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from runtime.models import AgentCreateRequest
from runtime.template_agent.base import BaseAgentTemplate



class BaseLangGraphAgent(BaseAgentTemplate, ABC):
    """
    Base class for agent templates.

    Agent classes ARE templates - they contain both template metadata
    (as class variables) and execution logic (as instance methods).
    """

    # Template Metadata (class variables)
    template_name: str = "LangGraph Base Agent"
    template_id: str = "langgraph-base-agent"
    template_version: str = "1.0.0"
    template_description: str = "LangGraph base agent template"

    # Configuration Schema (class variable)
    config_schema: type[BaseModel] = BaseModel

    def __init__(self, agent_data: AgentCreateRequest) -> None:
        """Initialize agent instance with configuration."""
        super().__init__(agent_data)

        # Build the agent graph
        self.graph = self._build_graph()

    @abstractmethod
    def _build_graph(self):
        """Build the LangGraph execution graph. Must be implemented by subclasses."""
        pass

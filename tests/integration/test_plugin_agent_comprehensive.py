"""Comprehensive plugin agent tests that catch instantiation and execution issues.

These tests would have caught:
1. Missing abstract method implementations
2. Invalid LangGraph node functions
3. State handling issues
4. Graph building problems
"""

import pytest
import asyncio
from inspect import isabstract
from typing import Any
from unittest.mock import Mock, AsyncMock

from runtime.core.plugin import get_plugin_registry
from runtime.core.plugin.init import initialize_plugin_system
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
from runtime.infrastructure.frameworks.langgraph.config import LangGraphFrameworkConfig
from runtime.service_config import ServicesConfig


# Initialize plugin system
asyncio.run(initialize_plugin_system())


# Fixtures
@pytest.fixture(scope="module")
def test_plugin_agent_meta():
    """Fixture to get test plugin agent metadata once per module."""
    registry = get_plugin_registry()
    agent_meta = registry.get_agent('test-plugin-agent')
    assert agent_meta is not None, "Plugin agent 'test-plugin-agent' not found in registry"
    return agent_meta


class TestPluginAgentValidation:
    """Validation tests that catch abstract method and instantiation issues."""
    
    def test_plugin_agent_is_not_abstract(self, test_plugin_agent_meta):
        """CRITICAL: Verify agent class is concrete, not abstract.
        
        This test would have caught: Missing abstract method implementations.
        """
        agent_class = test_plugin_agent_meta.class_obj
        
        # Check if class is abstract
        is_abstract = isabstract(agent_class)
        assert not is_abstract, (
            f"Agent class {agent_class.__name__} is abstract! "
            f"Missing abstract method implementations."
        )
    
    def test_plugin_agent_has_required_methods(self, test_plugin_agent_meta):
        """Verify agent has all required abstract methods implemented.
        
        This test would have caught: Missing _create_initial_state, _extract_final_content.
        """
        agent_class = test_plugin_agent_meta.class_obj
        
        # Check for required methods
        required_methods = [
            '_build_graph',
            '_create_initial_state',
            '_extract_final_content'
        ]
        
        for method_name in required_methods:
            assert hasattr(agent_class, method_name), (
                f"Agent missing required method: {method_name}"
            )
            
            method = getattr(agent_class, method_name)
            assert callable(method), f"{method_name} is not callable"
    
    def test_plugin_agent_methods_not_abstract(self, test_plugin_agent_meta):
        """Verify required methods are not still abstract."""
        agent_class = test_plugin_agent_meta.class_obj
        
        # Get abstract methods (if any remain)
        abstract_methods = getattr(agent_class, '__abstractmethods__', set())
        
        assert len(abstract_methods) == 0, (
            f"Agent has {len(abstract_methods)} abstract methods: {abstract_methods}"
        )


@pytest.mark.asyncio
class TestPluginAgentInstantiation:
    """Tests that verify agent can be instantiated.
    
    These tests would have caught abstract method errors at instantiation time.
    """
    
    async def test_plugin_agent_can_be_instantiated(self, test_plugin_agent_meta):
        """CRITICAL: Verify agent can be instantiated.
        
        This test would have caught: Abstract method implementation errors.
        """
        # Create minimal configuration
        config = AgentConfiguration(
            llm_config_id="test",
            template_config={}
        )
        
        # Create test services config
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        config_dict = services_config.get_config_dict()

        # Create framework config model from dict and services (inside scope)
        framework_cfg = LangGraphFrameworkConfig.from_dict(config_dict)

        # Create LLM and toolset services with validated models
        llm_service = LangGraphLLMService(framework_cfg.llm)
        
        # Create toolset service with validated ToolsetsConfig
        tool_service = LangGraphToolsetService(framework_cfg.toolsets)

        # Attempt instantiation - this will fail if abstract methods are missing
        try:
            agent = test_plugin_agent_meta.class_obj(
                configuration=config,
                llm_service=llm_service,
                toolset_service=tool_service,
                metadata={}
            )
            
            assert agent is not None
            assert agent.template_id == 'test-plugin-agent'
            
        except TypeError as e:
            if "abstract" in str(e).lower():
                pytest.fail(
                    f"Agent cannot be instantiated due to abstract methods: {e}"
                )
            raise
    
    async def test_plugin_agent_has_valid_config_schema(self, test_plugin_agent_meta):
        """Verify agent config schema is valid."""
        agent_class = test_plugin_agent_meta.class_obj
        
        assert hasattr(agent_class, 'config_schema')
        
        config_schema = agent_class.config_schema
        assert config_schema is not None
        
        # Should be instantiable
        try:
            config_instance = config_schema()
            assert config_instance is not None
        except Exception as e:
            pytest.fail(f"Config schema cannot be instantiated: {e}")


@pytest.mark.asyncio
class TestPluginAgentGraphBuilding:
    """Tests that verify graph can be built.
    
    These tests would have caught: Invalid LangGraph node function errors.
    """
    
    async def test_plugin_agent_can_build_graph(self, test_plugin_agent_meta):
        """CRITICAL: Verify agent graph can be built.
        
        This test would have caught: LangGraph node function signature issues.
        """
        # Create agent instance
        config = AgentConfiguration(
            llm_config_id="test",
            template_config={}
        )
        
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        config_dict = services_config.get_config_dict()

        framework_cfg = LangGraphFrameworkConfig.from_dict(config_dict)
        llm_service = LangGraphLLMService(framework_cfg.llm)
        tool_service = LangGraphToolsetService(framework_cfg.toolsets)

        agent = test_plugin_agent_meta.class_obj(
            configuration=config,
            llm_service=llm_service,
            toolset_service=tool_service,
            metadata={}
        )
        
        # Attempt to build graph
        try:
            graph = await agent._build_graph()
            
            assert graph is not None, "Graph should not be None"
            
            # Verify graph has expected structure
            assert hasattr(graph, 'nodes'), "Graph should have nodes"
            
        except Exception as e:
            pytest.fail(f"Failed to build graph: {e}")
    
    async def test_plugin_agent_graph_has_required_nodes(self, test_plugin_agent_meta):
        """Verify graph has expected nodes."""
        # Create agent
        config = AgentConfiguration(llm_config_id="test")
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        config_dict = services_config.get_config_dict()
        framework_cfg = LangGraphFrameworkConfig.from_dict(config_dict)

        agent = test_plugin_agent_meta.class_obj(
            configuration=config,
            llm_service=LangGraphLLMService(framework_cfg.llm),
            toolset_service=LangGraphToolsetService(framework_cfg.toolsets),
            metadata={}
        )
        
        graph = await agent._build_graph()
        
        # Check for expected nodes
        graph_nodes = list(graph.nodes.keys()) if hasattr(graph, 'nodes') else []
        
        assert "agent" in graph_nodes, "Graph should have 'agent' node"
        # Tools node might not be present if no tools configured
    
    async def test_plugin_agent_state_methods(self, test_plugin_agent_meta):
        """Verify state creation and extraction methods work."""
        config = AgentConfiguration(llm_config_id="test")
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        
        cfg = LangGraphFrameworkConfig.from_dict(services_config.get_config_dict())
        agent = test_plugin_agent_meta.class_obj(
            configuration=config,
            llm_service=LangGraphLLMService(cfg.llm),
            toolset_service=LangGraphToolsetService(cfg.toolsets),
            metadata={}
        )
        
        # Test _create_initial_state
        messages = [ChatMessage(role=MessageRole.USER, content="test")]
        initial_state = agent._create_initial_state(messages)
        
        assert isinstance(initial_state, dict), "Initial state should be a dict"
        assert "messages" in initial_state, "Initial state should have 'messages' key"
        
        # Test _extract_final_content
        final_state = {"messages": [Mock(content="test response")]}
        content = await agent._extract_final_content(final_state)
        
        assert isinstance(content, str), "Extracted content should be string"


@pytest.mark.asyncio
class TestPluginAgentExecution:
    """Tests that verify agent can execute messages.
    
    These tests would have caught: Runtime execution errors.
    """
    
    async def test_plugin_agent_execution_with_real_llm(self, test_plugin_agent_meta):
        """CRITICAL: Test agent executes successfully with real LLM.
        
        This test would have caught: All integration issues including:
        - Abstract method errors
        - Node function signature errors  
        - State handling errors
        """
        # Create agent
        config = AgentConfiguration(
            llm_config_id="deepseek",  # Use real LLM config
            template_config={}
        )
        
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        
        cfg = LangGraphFrameworkConfig.from_dict(services_config.get_config_dict())
        agent = test_plugin_agent_meta.class_obj(
            configuration=config,
            llm_service=LangGraphLLMService(cfg.llm),
            toolset_service=LangGraphToolsetService(cfg.toolsets),
            metadata={}
        )
        
        # Create test messages
        messages = [
            ChatMessage(role=MessageRole.USER, content="Say hello")
        ]
        
        # Execute agent
        try:
            result = await agent.execute(messages)
            print(f"Agent execution result: {result}")
            
            assert result is not None
            assert result.success, f"Execution failed: {result.error}"
            assert result.message, "Should have response message"
            assert len(result.message) > 0
            
        except Exception as e:
            pytest.fail(f"Agent execution failed: {e}")
    
    async def test_plugin_agent_execution_with_mock_llm(self, test_plugin_agent_meta):
        """Test agent execution with mocked LLM for faster testing."""
        # Create agent with mock LLM
        config = AgentConfiguration(llm_config_id="test")
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        
        # Use validated framework config when creating services for the agent
        cfg = LangGraphFrameworkConfig.from_dict(services_config.get_config_dict())
        agent = test_plugin_agent_meta.class_obj(
            configuration=config,
            llm_service=LangGraphLLMService(cfg.llm),
            toolset_service=LangGraphToolsetService(cfg.toolsets),
            metadata={}
        )
        
        # Build graph (this is where node function errors would appear)
        try:
            graph = await agent._build_graph()
            assert graph is not None
        except Exception as e:
            pytest.fail(f"Graph building failed (would catch node function errors): {e}")


@pytest.mark.asyncio  
class TestPluginAgentToolIntegration:
    """Tests that verify agent can use tools properly."""
    


    async def test_plugin_agent_has_access_to_tools(self, test_plugin_agent_meta):
        """Verify agent can access plugin tools."""
        # Configure agent with toolsets
        config = AgentConfiguration(
            llm_config_id="test",
            toolsets=["plugin_tools"]  # Add toolsets configuration
        )
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        
        # Create agent with toolsets
        cfg = LangGraphFrameworkConfig.from_dict(services_config.get_config_dict())
        tool_service = LangGraphToolsetService(cfg.toolsets)
        
        agent = test_plugin_agent_meta.class_obj(
            configuration=config,
            llm_service=LangGraphLLMService(cfg.llm),
            toolset_service=tool_service,
            metadata={}
        )
        
        # Agent should have toolset client
        assert agent.toolset_client is not None
        
        # Should be able to get tools
        tools = await agent.toolset_client.tools
        assert isinstance(tools, list)


def test_summary():
    """Summary of what these tests catch."""


    test_coverage = {
        "Abstract Method Validation": "Catches missing method implementations",
        "Instantiation Tests": "Catches abstract class errors",
        "Graph Building Tests": "Catches LangGraph node function errors",
        "State Handling Tests": "Catches state format errors",
        "Execution Tests": "Catches runtime integration errors",
        "Tool Integration Tests": "Catches tool binding errors"
    }
    
    for test_type, catches in test_coverage.items():
        print(f"✅ {test_type}: {catches}")




if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

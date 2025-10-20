"""E2E integration tests for plugin system.

This test suite verifies:
- Plugin tool discovery and loading
- Plugin agent discovery and loading
- Tool execution in agent workflows
- File operations via plugin tools
- Web operations via plugin tools
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import Any

from runtime.core.plugin import get_plugin_registry
from runtime.core.plugin.init import initialize_plugin_system


# Initialize plugin system at module load time
asyncio.run(initialize_plugin_system())

# Fixtures
@pytest.fixture(scope="module")
def agent_meta():
    """Fixture to get test plugin agent metadata once per module."""
    registry = get_plugin_registry()
    agent_meta = registry.get_agent('test-plugin-agent')
    assert agent_meta is not None, "Plugin agent 'test-plugin-agent' not found in registry"
    return agent_meta


class TestPluginToolDiscovery:
    """Test plugin tool discovery and registration."""
    
    def test_file_tools_discovered(self):
        """Test that file tools are discovered from plugins."""
        registry = get_plugin_registry()
        
        # Check for file tools
        file_tools = [
            'read_lines',
            'grep_file', 
            'create_file',
            'delete_file'
        ]
        
        for tool_name in file_tools:
            tool_meta = registry.get_tool(tool_name)
            assert tool_meta is not None, f"Tool {tool_name} not found in registry"
            assert tool_meta.plugin_type == "tool"
            assert tool_meta.plugin_id == tool_name
    
    def test_web_tools_discovered(self):
        """Test that web tools are discovered from plugins."""
        registry = get_plugin_registry()
        
        # Check for web tools
        web_tools = [
            'fetch_url',
            'parse_url'
        ]
        
        for tool_name in web_tools:
            tool_meta = registry.get_tool(tool_name)
            assert tool_meta is not None, f"Tool {tool_name} not found in registry"
            assert tool_meta.plugin_type == "tool"
            assert tool_meta.plugin_id == tool_name
    
    def test_tool_instantiation(self):
        """Test that discovered tools can be instantiated."""
        registry = get_plugin_registry()
        
        # Test instantiating read_lines tool
        tool_meta = registry.get_tool('read_lines')
        assert tool_meta is not None
        
        tool_instance = tool_meta.class_obj()
        assert tool_instance.name == 'read_lines'
        assert hasattr(tool_instance, '_run')
        assert hasattr(tool_instance, 'description')


class TestPluginAgentDiscovery:
    """Test plugin agent discovery and registration."""
    
    def test_agent_has_metadata(self, agent_meta):
        """Test that discovered agent has correct metadata."""
        registry = get_plugin_registry()
                
        # Check template metadata
        agent_class = agent_meta.class_obj
        assert hasattr(agent_class, 'template_id')
        assert hasattr(agent_class, 'template_name')
        assert hasattr(agent_class, 'template_version')
        assert hasattr(agent_class, 'template_description')


class TestFileToolsExecution:
    """Test file tool execution."""
    
    def test_create_file_tool(self):
        """Test creating a file via plugin tool."""
        registry = get_plugin_registry()
        tool_meta = registry.get_tool('create_file')
        assert tool_meta is not None
        
        tool = tool_meta.class_obj()
        
        # Create a test file in temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            
            # Change to temp directory for security validation
            import os
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                result = tool._run(
                    filename="test.txt",
                    content="Hello, World!",
                    overwrite=False
                )
                
                assert "Successfully created file" in result
                assert test_file.exists()
                assert test_file.read_text() == "Hello, World!"
            finally:
                os.chdir(original_dir)
    
    def test_read_lines_tool(self):
        """Test reading lines from a file via plugin tool."""
        registry = get_plugin_registry()
        tool_meta = registry.get_tool('read_lines')
        assert tool_meta is not None
        
        tool = tool_meta.class_obj()
        
        # Create a test file and read it
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("Line 1\nLine 2\nLine 3\n")
            
            import os
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                result = tool._run(filename="test.txt", start=1, end=2)
                
                assert "Line 1" in result
                assert "Line 2" in result
                assert "Line 3" not in result
            finally:
                os.chdir(original_dir)
    
    def test_grep_file_tool(self):
        """Test searching in a file via plugin tool."""
        registry = get_plugin_registry()
        tool_meta = registry.get_tool('grep_file')
        assert tool_meta is not None
        
        tool = tool_meta.class_obj()
        
        # Create a test file and search it
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("Hello World\nFoo Bar\nHello Again\n")
            
            import os
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                result = tool._run(
                    filename="test.txt",
                    pattern="Hello",
                    ignore_case=False,
                    line_numbers=True
                )
                
                assert "1: Hello World" in result
                assert "3: Hello Again" in result
                assert "Foo Bar" not in result
            finally:
                os.chdir(original_dir)
    
    def test_delete_file_tool(self):
        """Test deleting a file via plugin tool."""
        registry = get_plugin_registry()
        tool_meta = registry.get_tool('delete_file')
        assert tool_meta is not None
        
        tool = tool_meta.class_obj()
        
        # Create and delete a test file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("To be deleted")
            
            import os
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                assert test_file.exists()
                
                result = tool._run(filename="test.txt", confirm=True)
                
                assert "Successfully deleted" in result
                assert not test_file.exists()
            finally:
                os.chdir(original_dir)


class TestWebToolsExecution:
    """Test web tool execution."""
    
    def test_parse_url_tool(self):
        """Test parsing URL via plugin tool."""
        registry = get_plugin_registry()
        tool_meta = registry.get_tool('parse_url')
        assert tool_meta is not None
        
        tool = tool_meta.class_obj()
        
        result = tool._run(url="https://example.com:8080/path?query=value#fragment")
        
        assert "scheme: https" in result
        assert "hostname: example.com" in result
        assert "port: 8080" in result
        assert "/path" in result
        assert "query=value" in result
        assert "fragment" in result
    
    @pytest.mark.asyncio
    async def test_fetch_url_tool_httpbin(self):
        """Test fetching URL via plugin tool using httpbin."""
        registry = get_plugin_registry()
        tool_meta = registry.get_tool('fetch_url')
        assert tool_meta is not None
        
        tool = tool_meta.class_obj()
        
        # Use httpbin.org for testing (public HTTP testing service)
        # Since we're in an async context, call the async method directly
        result = await tool._async_run(
            url="https://httpbin.org/json",
            save_to_file=False,
            follow_redirects=True,
            headers={}
        )
        
        # Should get JSON response
        assert "Status: 200" in result or "slideshow" in result.lower()


@pytest.mark.asyncio
class TestPluginAgentE2E:
    """E2E tests for plugin agent with tools."""

    async def test_plugin_agent_not_abstract(self, agent_meta):
        """CRITICAL: Verify plugin agent is not abstract.
        
        This test catches missing abstract method implementations.
        """
        from inspect import isabstract
                
        agent_class = agent_meta.class_obj
        is_abstract = isabstract(agent_class)
        
        assert not is_abstract, (
            f"Plugin agent {agent_class.__name__} is abstract! "
            f"Check for missing abstract method implementations: "
            f"_create_initial_state, _extract_final_content, _build_graph"
        )

    async def test_plugin_agent_can_be_instantiated(self, agent_meta):
        """CRITICAL: Verify plugin agent can be instantiated.
        
        This test catches:
        - Missing abstract method implementations
        - Invalid __init__ signatures
        - Configuration errors
        """
        from runtime.domain.value_objects.agent_configuration import AgentConfiguration
        from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
        from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
        from runtime.infrastructure.frameworks.langgraph.config import LangGraphFrameworkConfig
        from runtime.service_config import ServicesConfig
                
        # Create configuration
        config = AgentConfiguration(
            llm_config_id="test",
            template_config={}
        )
        
        # Create services with validated pydantic models
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        config_dict = services_config.get_config_dict()
        
        # Convert to validated framework config
        framework_cfg = LangGraphFrameworkConfig.from_dict(config_dict)
        llm_service = LangGraphLLMService(framework_cfg.llm)
        tool_service = LangGraphToolsetService(framework_cfg.toolsets)
        
        # Attempt instantiation
        try:
            agent = agent_meta.class_obj(
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
                    f"Agent cannot be instantiated - missing abstract methods: {e}"
                )
            raise

    async def test_plugin_agent_can_build_graph(self, agent_meta):
        """CRITICAL: Verify plugin agent graph can be built.
        
        This test catches:
        - Invalid LangGraph node functions
        - State handling errors
        - Graph structure issues
        """
        from runtime.domain.value_objects.agent_configuration import AgentConfiguration
        from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
        from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
        from runtime.infrastructure.frameworks.langgraph.config import LangGraphFrameworkConfig
        from runtime.service_config import ServicesConfig
                
        # Create agent with validated pydantic models
        config = AgentConfiguration(llm_config_id="test")
        services_config = ServicesConfig(config_file="config/test-services-config.json")
        config_dict = services_config.get_config_dict()
        
        # Convert to validated framework config
        framework_cfg = LangGraphFrameworkConfig.from_dict(config_dict)
        
        agent = agent_meta.class_obj(
            configuration=config,
            llm_service=LangGraphLLMService(framework_cfg.llm),
            toolset_service=LangGraphToolsetService(framework_cfg.toolsets),
            metadata={}
        )
        
        # Build graph
        try:
            graph = await agent._build_graph()
            
            assert graph is not None, "Graph build returned None"
            assert hasattr(graph, 'nodes'), "Graph should have nodes attribute"
            
            # Verify node structure
            nodes = list(graph.nodes.keys()) if hasattr(graph, 'nodes') else []
            assert "agent" in nodes, "Graph should have 'agent' node"
            
        except Exception as e:
            pytest.fail(
                f"Graph building failed (check node function signatures): {e}"
            )
    
    async def test_plugin_tools_available_for_agents(self):
        """Test that plugin tools can be loaded for agent use."""
        registry = get_plugin_registry()
        
        # Get all file tools
        file_tool_names = ['read_lines', 'grep_file', 'create_file', 'delete_file']
        
        tools = []
        for tool_name in file_tool_names:
            tool_meta = registry.get_tool(tool_name)
            assert tool_meta is not None
            tool = tool_meta.class_obj()
            tools.append(tool)
        
        # Should have 4 file tools
        assert len(tools) == 4
        
        # All should be instantiated and have required attributes
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, '_run')

    async def test_plugin_agent_template_available(self, agent_meta):
        """Test that test-plugin-agent template is available."""        
        # Should be able to access the class
        agent_class = agent_meta.class_obj
        assert agent_class is not None
        assert hasattr(agent_class, 'template_id')
        assert agent_class.template_id == 'test-plugin-agent'


@pytest.mark.asyncio
class TestPluginSystemIntegration:
    """Integration tests for complete plugin system."""
    
    async def test_all_tools_from_plugins(self):
        """Verify all tools come from plugin system."""
        registry = get_plugin_registry()
        
        # List all tools
        all_tools = registry.list_tools()
        
        # Should have at least file and web tools
        tool_names = [t.plugin_id for t in all_tools]
        
        expected_tools = [
            'read_lines', 'grep_file', 'create_file', 'delete_file',  # file tools
            'fetch_url', 'parse_url'  # web tools
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Expected tool {expected} not found in plugins"
    
    async def test_plugin_tool_metadata(self):
        """Verify plugin tools have proper metadata."""
        registry = get_plugin_registry()
        
        tool_meta = registry.get_tool('read_lines')
        assert tool_meta is not None
        
        # Should have version info
        tool_instance = tool_meta.class_obj()
        assert hasattr(tool_instance, '__version__')
        assert tool_instance.__version__ == "1.0.0"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

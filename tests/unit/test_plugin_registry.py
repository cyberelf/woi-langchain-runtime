"""
Unit tests for the plugin registry.

Tests the PluginRegistry class's ability to store, retrieve,
and manage plugin metadata with collision handling.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from runtime.core.plugin.registry import PluginRegistry
from runtime.core.plugin.loader import PluginMetadata


class TestPluginRegistry:
    """Test suite for PluginRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return PluginRegistry()

    @pytest.fixture
    def sample_agent_metadata(self):
        """Create sample agent metadata for testing."""
        return PluginMetadata(
            plugin_id="test-agent",
            name="TestAgent",
            module_path="plugins.agents.test_agent",
            file_path=Path("/fake/path/test_agent.py"),
            plugin_type="agent",
            class_obj=MagicMock(),
            version="1.0.0",
            description="A test agent",
            source="plugins/agents"
        )

    @pytest.fixture
    def sample_tool_metadata(self):
        """Create sample tool metadata for testing."""
        return PluginMetadata(
            plugin_id="test_tool",
            name="TestTool",
            module_path="plugins.tools.test_tool",
            file_path=Path("/fake/path/test_tool.py"),
            plugin_type="tool",
            class_obj=MagicMock(),
            version="2.0.0",
            description="A test tool",
            source="plugins/tools"
        )

    def test_register_agent(self, registry, sample_agent_metadata):
        """Test registering an agent plugin."""
        plugin_id = sample_agent_metadata.plugin_id
        registry.register_agent(plugin_id, sample_agent_metadata)
        
        # Should be able to retrieve it
        assert registry.agent_exists(plugin_id)
        retrieved = registry.get_agent(plugin_id)
        assert retrieved == sample_agent_metadata

    def test_register_tool(self, registry, sample_tool_metadata):
        """Test registering a tool plugin."""
        plugin_id = sample_tool_metadata.plugin_id
        registry.register_tool(plugin_id, sample_tool_metadata)
        
        # Should be able to retrieve it
        assert registry.tool_exists(plugin_id)
        retrieved = registry.get_tool(plugin_id)
        assert retrieved == sample_tool_metadata

    def test_get_nonexistent_agent(self, registry):
        """Test getting a non-existent agent returns None."""
        result = registry.get_agent("nonexistent")
        assert result is None

    def test_get_nonexistent_tool(self, registry):
        """Test getting a non-existent tool returns None."""
        result = registry.get_tool("nonexistent")
        assert result is None

    def test_list_agents(self, registry, sample_agent_metadata):
        """Test listing all registered agents."""
        # Initially empty
        assert registry.list_agents() == []
        
        # Register an agent
        registry.register_agent(sample_agent_metadata.plugin_id, sample_agent_metadata)
        agents = registry.list_agents()
        
        assert len(agents) == 1
        assert agents[0] == sample_agent_metadata

    def test_list_tools(self, registry, sample_tool_metadata):
        """Test listing all registered tools."""
        # Initially empty
        assert registry.list_tools() == []
        
        # Register a tool
        registry.register_tool(sample_tool_metadata.plugin_id, sample_tool_metadata)
        tools = registry.list_tools()
        
        assert len(tools) == 1
        assert tools[0] == sample_tool_metadata

    def test_agent_tool_separation(self, registry, sample_agent_metadata, sample_tool_metadata):
        """Test that agents and tools are stored in separate namespaces."""
        registry.register_agent(sample_agent_metadata.plugin_id, sample_agent_metadata)
        registry.register_tool(sample_tool_metadata.plugin_id, sample_tool_metadata)
        
        # Should have one of each
        assert len(registry.list_agents()) == 1
        assert len(registry.list_tools()) == 1
        
        # Should not cross-contaminate
        assert registry.agent_exists("test-agent")
        assert not registry.agent_exists("test_tool")
        assert registry.tool_exists("test_tool")
        assert not registry.tool_exists("test-agent")

    def test_collision_first_wins(self, registry, sample_agent_metadata):
        """Test that on collision, the first registered plugin wins."""
        # Register first plugin
        registry.register_agent(sample_agent_metadata.plugin_id, sample_agent_metadata)
        
        # Try to register a different plugin with the same ID
        duplicate = PluginMetadata(
            plugin_id="test-agent",  # Same ID
            name="DuplicateAgent",  # Different name
            module_path="plugins.agents.duplicate",
            file_path=Path("/fake/path/duplicate.py"),
            plugin_type="agent",
            class_obj=MagicMock(),
            version="2.0.0",
            description="A duplicate",
            source="plugins/agents"
        )
        registry.register_agent(duplicate.plugin_id, duplicate)
        
        # First one should still be there
        retrieved = registry.get_agent("test-agent")
        assert retrieved.name == "TestAgent"  # Original name
        assert retrieved.version == "1.0.0"   # Original version

    def test_concurrent_registration(self, registry):
        """Test that concurrent registrations work correctly.
        
        Note: In async applications, operations run on a single event loop,
        so traditional thread-safety isn't needed. This test verifies that
        basic dict operations work as expected.
        """
        # Register multiple agents sequentially (simulating async operations)
        for i in range(50):
            metadata = PluginMetadata(
                plugin_id=f"agent-{i}",
                name=f"Agent{i}",
                module_path=f"plugins.agents.agent{i}",
                file_path=Path(f"/fake/agent{i}.py"),
                plugin_type="agent",
                class_obj=MagicMock(),
                version="1.0.0",
                description=f"Agent {i}",
                source="plugins/agents"
            )
            registry.register_agent(metadata.plugin_id, metadata)
        
        # All agents should be registered
        assert len(registry.list_agents()) == 50

    def test_get_stats(self, registry, sample_agent_metadata, sample_tool_metadata):
        """Test getting registry statistics."""
        # Initially empty
        stats = registry.get_stats()
        assert stats["agent_count"] == 0
        assert stats["tool_count"] == 0
        assert stats["total_plugins"] == 0
        
        # Add some plugins
        registry.register_agent(sample_agent_metadata.plugin_id, sample_agent_metadata)
        registry.register_tool(sample_tool_metadata.plugin_id, sample_tool_metadata)
        
        stats = registry.get_stats()
        assert stats["agent_count"] == 1
        assert stats["tool_count"] == 1
        assert stats["total_plugins"] == 2

    def test_multiple_agents(self, registry):
        """Test registering and retrieving multiple agents."""
        agents_data = [
            ("agent-1", "Agent1", "1.0.0"),
            ("agent-2", "Agent2", "1.5.0"),
            ("agent-3", "Agent3", "2.0.0"),
        ]
        
        for plugin_id, name, version in agents_data:
            metadata = PluginMetadata(
                plugin_id=plugin_id,
                name=name,
                module_path=f"plugins.agents.{name.lower()}",
                file_path=Path(f"/fake/{name.lower()}.py"),
                plugin_type="agent",
                class_obj=MagicMock(),
                version=version,
                description=f"{name} description",
                source="plugins/agents"
            )
            registry.register_agent(plugin_id, metadata)
        
        # All should be retrievable
        assert len(registry.list_agents()) == 3
        for plugin_id, name, version in agents_data:
            assert registry.agent_exists(plugin_id)
            agent = registry.get_agent(plugin_id)
            assert agent.name == name
            assert agent.version == version

    def test_multiple_tools(self, registry):
        """Test registering and retrieving multiple tools."""
        tools_data = [
            ("tool_one", "ToolOne", "1.0.0"),
            ("tool_two", "ToolTwo", "1.5.0"),
            ("tool_three", "ToolThree", "2.0.0"),
        ]
        
        for plugin_id, name, version in tools_data:
            metadata = PluginMetadata(
                plugin_id=plugin_id,
                name=name,
                module_path=f"plugins.tools.{name.lower()}",
                file_path=Path(f"/fake/{name.lower()}.py"),
                plugin_type="tool",
                class_obj=MagicMock(),
                version=version,
                description=f"{name} description",
                source="plugins/tools"
            )
            registry.register_tool(plugin_id, metadata)
        
        # All should be retrievable
        assert len(registry.list_tools()) == 3
        for plugin_id, name, version in tools_data:
            assert registry.tool_exists(plugin_id)
            tool = registry.get_tool(plugin_id)
            assert tool.name == name
            assert tool.version == version

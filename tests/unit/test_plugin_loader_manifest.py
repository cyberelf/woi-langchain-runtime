"""
Unit tests for the manifest-based plugin loader.

Tests the PluginLoader's ability to load plugins from __init__.py manifests
containing __tools__ or __agents__ lists.
"""

import tempfile
import pytest
from pathlib import Path

from runtime.core.plugin.loader import PluginLoader, PluginMetadata
from langchain_core.tools import BaseTool


class TestManifestPluginLoader:
    """Test suite for manifest-based PluginLoader."""

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create a temporary directory for test plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def _simple_validator(self, cls) -> bool:
        """Simple validator for tests."""
        try:
            return issubclass(cls, BaseTool) and cls != BaseTool
        except TypeError:
            return False

    def test_load_tools_from_manifest(self, temp_plugin_dir):
        """Test loading tools from __tools__ list in __init__.py."""
        # Create a tool module
        tool_file = temp_plugin_dir / "test_tool.py"
        tool_file.write_text("""
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class TestToolInput(BaseModel):
    text: str = Field(description="Input text")

class TestTool(BaseTool):
    name: str = "test_tool"
    description: str = "A test tool"
    args_schema: type[BaseModel] = TestToolInput
    
    __version__: str = "1.0.0"
    
    def _run(self, text: str) -> str:
        return f"Processed: {text}"
""")

        # Create manifest
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
from .test_tool import TestTool

__tools__ = [
    TestTool,
]
""")

        # Load plugins
        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Assertions
        assert len(plugins) == 1
        assert "test_tool" in plugins
        plugin = plugins["test_tool"]
        assert plugin.name == "TestTool"
        assert plugin.plugin_id == "test_tool"
        assert plugin.version == "1.0.0"
        assert plugin.plugin_type == "tool"

    def test_load_multiple_tools_from_manifest(self, temp_plugin_dir):
        """Test loading multiple tools from manifest."""
        # Create tool modules
        tool_file_1 = temp_plugin_dir / "tool_one.py"
        tool_file_1.write_text("""
from langchain_core.tools import BaseTool

class ToolOne(BaseTool):
    name: str = "tool_one"
    description: str = "First tool"
    
    def _run(self) -> str:
        return "one"
""")

        tool_file_2 = temp_plugin_dir / "tool_two.py"
        tool_file_2.write_text("""
from langchain_core.tools import BaseTool

class ToolTwo(BaseTool):
    name: str = "tool_two"
    description: str = "Second tool"
    
    def _run(self) -> str:
        return "two"
""")

        # Create manifest
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
from .tool_one import ToolOne
from .tool_two import ToolTwo

__tools__ = [
    ToolOne,
    ToolTwo,
]
""")

        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should find both tools
        assert len(plugins) == 2
        assert "tool_one" in plugins
        assert "tool_two" in plugins

    def test_selective_loading(self, temp_plugin_dir):
        """Test that only tools in manifest are loaded."""
        # Create two tool files
        tool_file_1 = temp_plugin_dir / "included_tool.py"
        tool_file_1.write_text("""
from langchain_core.tools import BaseTool

class IncludedTool(BaseTool):
    name: str = "included"
    description: str = "This tool is in manifest"
    
    def _run(self) -> str:
        return "included"
""")

        tool_file_2 = temp_plugin_dir / "excluded_tool.py"
        tool_file_2.write_text("""
from langchain_core.tools import BaseTool

class ExcludedTool(BaseTool):
    name: str = "excluded"
    description: str = "This tool is NOT in manifest"
    
    def _run(self) -> str:
        return "excluded"
""")

        # Create manifest - only include one tool
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
from .included_tool import IncludedTool
# from .excluded_tool import ExcludedTool  # Commented out

__tools__ = [
    IncludedTool,
    # ExcludedTool,  # Not included
]
""")

        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should only find the included tool
        assert len(plugins) == 1
        assert "included" in plugins
        assert "excluded" not in plugins

    def test_missing_manifest(self, temp_plugin_dir):
        """Test handling of directory without __init__.py."""
        # Don't create __init__.py
        
        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should find no plugins but not crash
        assert len(plugins) == 0

    def test_manifest_without_attribute(self, temp_plugin_dir):
        """Test manifest without __tools__ attribute."""
        # Create manifest without __tools__
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
# Empty manifest - no __tools__ defined
pass
""")

        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should find no plugins
        assert len(plugins) == 0

    def test_manifest_attribute_not_list(self, temp_plugin_dir):
        """Test manifest where __tools__ is not a list."""
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
__tools__ = "not a list"
""")

        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should handle gracefully
        assert len(plugins) == 0

    def test_invalid_plugin_class(self, temp_plugin_dir):
        """Test that invalid classes are skipped."""
        # Create tool module
        tool_file = temp_plugin_dir / "bad_tool.py"
        tool_file.write_text("""
# Not a BaseTool subclass
class BadTool:
    name: str = "bad_tool"
    
    def run(self) -> str:
        return "bad"
""")

        # Create manifest
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
from .bad_tool import BadTool

__tools__ = [
    BadTool,  # Will fail validation
]
""")

        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should skip invalid class
        assert len(plugins) == 0

    def test_non_class_in_manifest(self, temp_plugin_dir):
        """Test that non-class items are skipped."""
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
__tools__ = [
    "not a class",
    42,
    None,
]
""")

        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should skip all invalid items
        assert len(plugins) == 0

    def test_import_error_handling(self, temp_plugin_dir):
        """Test handling of import errors in manifest."""
        # Create manifest with bad import
        manifest = temp_plugin_dir / "__init__.py"
        manifest.write_text("""
from .nonexistent_module import SomeTool

__tools__ = [
    SomeTool,
]
""")

        loader = PluginLoader(
            plugin_dirs=[temp_plugin_dir],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should handle import error gracefully
        assert len(plugins) == 0

    def test_multiple_directories(self, temp_plugin_dir):
        """Test loading from multiple plugin directories."""
        # Create second directory
        with tempfile.TemporaryDirectory() as tmpdir2:
            dir2 = Path(tmpdir2)
            
            # Create tool in first directory
            tool1 = temp_plugin_dir / "tool1.py"
            tool1.write_text("""
from langchain_core.tools import BaseTool

class Tool1(BaseTool):
    name: str = "tool_1"
    description: str = "Tool 1"
    
    def _run(self) -> str:
        return "1"
""")
            manifest1 = temp_plugin_dir / "__init__.py"
            manifest1.write_text("""
from .tool1 import Tool1
__tools__ = [Tool1]
""")
            
            # Create tool in second directory
            tool2 = dir2 / "tool2.py"
            tool2.write_text("""
from langchain_core.tools import BaseTool

class Tool2(BaseTool):
    name: str = "tool_2"
    description: str = "Tool 2"
    
    def _run(self) -> str:
        return "2"
""")
            manifest2 = dir2 / "__init__.py"
            manifest2.write_text("""
from .tool2 import Tool2
__tools__ = [Tool2]
""")
            
            loader = PluginLoader(
                plugin_dirs=[temp_plugin_dir, dir2],
                validator=self._simple_validator,
                plugin_type="tool",
                manifest_attr="__tools__"
            )
            plugins = loader.discover_plugins()
            
            # Should find tools from both directories
            assert len(plugins) == 2
            assert "tool_1" in plugins
            assert "tool_2" in plugins

    def test_nonexistent_directory(self):
        """Test handling of nonexistent directory."""
        loader = PluginLoader(
            plugin_dirs=[Path("/nonexistent/path")],
            validator=self._simple_validator,
            plugin_type="tool",
            manifest_attr="__tools__"
        )
        plugins = loader.discover_plugins()

        # Should handle gracefully
        assert len(plugins) == 0

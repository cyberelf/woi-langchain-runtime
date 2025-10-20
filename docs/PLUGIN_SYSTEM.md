# Plugin System - Manifest-Based Registration

## Overview

The plugin system uses **manifest-based registration** where plugins are explicitly declared in `__init__.py` files. This provides clear control over which plugins are loaded and in what order.

## Architecture

### Key Components

1. **Plugin Manifests** (`__init__.py`): Explicitly declare plugins to load
2. **PluginLoader**: Reads manifests and loads declared plugins  
3. **PluginRegistry**: Central registry for all loaded plugins
4. **Validators**: Check plugin classes meet requirements

### Plugin Types

- **Tools**: LangChain BaseTool subclasses for agent actions
- **Agents**: LangGraph agent templates for specific workflows

## Creating Plugins

### Tool Plugins

**1. Create your tool class** in `plugins/tools/my_tool.py`:

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    text: str = Field(description="Input text")

class MyTool(BaseTool):
    """Description of what my tool does."""
    
    name: str = "my_tool"
    description: str = "A custom tool that processes text"
    args_schema: type[BaseModel] = MyToolInput
    __version__: str = "1.0.0"
    
    def _run(self, text: str) -> str:
        """Synchronous implementation."""
        return f"Processed: {text}"
    
    async def _arun(self, text: str) -> str:
        """Async implementation (optional)."""
        return self._run(text)
```

**2. Register in manifest** `plugins/tools/__init__.py`:

```python
from .my_tool import MyTool
from .other_tool import OtherTool

__tools__ = [
    MyTool,
    OtherTool,
]
```

### Agent Plugins

**1. Create your agent** in `plugins/agents/my_agent.py`:

```python
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphAgent
from langgraph.graph import StateGraph, START, END

class MyAgent(BaseLangGraphAgent):
    """Description of what the agent does."""
    
    template_id = "my-agent"
    __version__ = "1.0.0"
    
    def build_graph(self, state_class, config):
        """Build the agent's workflow graph."""
        graph = StateGraph(state_class)
        
        # Define nodes and edges
        graph.add_node("process", self._process_node)
        graph.add_edge(START, "process")
        graph.add_edge("process", END)
        
        return graph.compile()
    
    def _process_node(self, state):
        """Process node implementation."""
        return {"result": "processed"}
```

**2. Register in manifest** `plugins/agents/__init__.py`:

```python
from .my_agent import MyAgent
from .test_agent import TestPluginAgent

__agents__ = [
    MyAgent,
    TestPluginAgent,
]
```

## Managing Plugins

### Enable/Disable Plugins

Simply comment out plugins in the manifest to disable them:

```python
# plugins/tools/__init__.py
from .file_tools import ReadLinesTool, CreateFileTool
from .web_tools import FetchUrlTool

__tools__ = [
    ReadLinesTool,
    CreateFileTool,
    # FetchUrlTool,  # Disabled for now
]
```

### Load Order

Plugins are loaded in the order they appear in the `__tools__` or `__agents__` list.

### Multiple Directories

The system can load from multiple plugin directories:

```python
# Configured in settings.py
plugin_root_dir = "plugins"
plugin_agents_dir = "agents"
plugin_tools_dir = "tools"
custom_agents_dir = "/path/to/custom/agents"  # Optional
```

## Plugin Requirements

### Tool Requirements

- Must inherit from `langchain_core.tools.BaseTool`
- Must define `name` field (str)
- Must define `description` field (str)  
- Must implement `_run()` method
- Should define `args_schema` for input validation
- Optional: Define `__version__` attribute

### Agent Requirements

- Must inherit from `BaseLangGraphAgent`
- Must define `template_id` attribute (str)
- Must implement `build_graph()` method
- Optional: Define `__version__` attribute

## Plugin Discovery Process

1. **Startup**: `initialize_plugin_system()` is called on application start
2. **Directory Scan**: System checks configured plugin directories
3. **Manifest Loading**: Imports each `__init__.py` manifest
4. **List Extraction**: Reads `__tools__` or `__agents__` list
5. **Validation**: Validates each class meets requirements
6. **Registration**: Registers valid plugins in global registry
7. **Availability**: Plugins become available to agents and API

## Error Handling

### Import Errors

If a plugin fails to import, it's logged and skipped:

```
ERROR Failed to import manifest plugins/tools/__init__.py: No module named 'my_dependency'
```

**Solution**: Check dependencies are installed

### Validation Errors

If a plugin fails validation:

```
ERROR Plugin class MyTool failed validation. Skipping.
```

**Solution**: Check plugin meets requirements (base class, required attributes)

### Duplicate IDs

If two plugins have the same ID:

```
WARNING Duplicate plugin ID 'my_tool'. Using first occurrence.
```

**Solution**: Ensure unique `name` or `template_id` values

## Best Practices

### 1. Explicit Registration

✅ **Good**: Explicitly list all plugins in manifest

```python
__tools__ = [
    ToolA,
    ToolB,
    ToolC,
]
```

❌ **Bad**: Dynamic registration or glob imports

### 2. Version Management

Always define `__version__` for tracking:

```python
class MyTool(BaseTool):
    __version__ = "1.0.0"
```

### 3. Clear Documentation

Provide clear docstrings and descriptions:

```python
class MyTool(BaseTool):
    """
    Process text data and extract key information.
    
    Use this tool when you need to analyze text content.
    """
    name: str = "text_processor"
    description: str = "Analyzes text and extracts key information"
```

### 4. Input Validation

Use Pydantic models for type-safe inputs:

```python
class MyToolInput(BaseModel):
    text: str = Field(description="Text to process", min_length=1)
    mode: str = Field(description="Processing mode", pattern="^(fast|thorough)$")

class MyTool(BaseTool):
    args_schema: type[BaseModel] = MyToolInput
```

### 5. Error Handling

Handle errors gracefully in tools:

```python
def _run(self, text: str) -> str:
    try:
        return process(text)
    except ProcessingError as e:
        return f"Error processing text: {str(e)}"
```

## Testing Plugins

### Unit Testing

```python
def test_my_tool():
    tool = MyTool()
    result = tool._run(text="Hello")
    assert result == "Processed: Hello"
```

### Integration Testing

```python
async def test_tool_registration():
    from runtime.core.plugin.registry import get_plugin_registry
    
    registry = get_plugin_registry()
    tool_meta = registry.get_tool('my_tool')
    
    assert tool_meta is not None
    assert tool_meta.name == "MyTool"
```

## Migration from Auto-Discovery

If you're migrating from an auto-discovery system:

1. **Create manifests**: Add `__init__.py` to plugin directories
2. **List plugins**: Import and list all plugin classes
3. **Test**: Verify all plugins load correctly
4. **Remove old files**: Clean up any discovery-specific code

## Troubleshooting

### Problem: No plugins loaded

**Checklist**:
- ✓ `__init__.py` exists in plugin directory
- ✓ `__tools__` or `__agents__` list is defined
- ✓ Plugins are imported at top of manifest
- ✓ Plugin classes meet requirements

### Problem: Import errors

**Solutions**:
- Check all dependencies are installed
- Verify relative imports use correct paths
- Check for circular imports

### Problem: Plugin not available in agents

**Solutions**:
- Verify plugin passed validation
- Check plugin registered successfully (check logs)
- Ensure plugin ID doesn't conflict with existing plugins

## Example Complete Setup

### Directory Structure

```
plugins/
├── agents/
│   ├── __init__.py          # Agent manifest
│   ├── data_agent.py        # Data processing agent
│   └── chat_agent.py        # Chat agent
└── tools/
    ├── __init__.py          # Tool manifest
    ├── file_tools.py        # File operation tools
    ├── web_tools.py         # Web operation tools
    └── custom_tools.py      # Custom tools
```

### Tools Manifest

```python
# plugins/tools/__init__.py
from .file_tools import ReadLinesTool, CreateFileTool, GrepFileTool, DeleteFileTool
from .web_tools import FetchUrlTool, ParseUrlTool
from .custom_tools import CustomProcessingTool

__tools__ = [
    # File operations
    ReadLinesTool,
    CreateFileTool,
    GrepFileTool,
    DeleteFileTool,
    
    # Web operations
    FetchUrlTool,
    ParseUrlTool,
    
    # Custom tools
    CustomProcessingTool,
]

__all__ = [
    "__tools__",
    "ReadLinesTool",
    "CreateFileTool",
    "GrepFileTool",
    "DeleteFileTool",
    "FetchUrlTool",
    "ParseUrlTool",
    "CustomProcessingTool",
]
```

### Agents Manifest

```python
# plugins/agents/__init__.py
from .data_agent import DataAgent
from .chat_agent import ChatAgent

__agents__ = [
    DataAgent,
    ChatAgent,
]

__all__ = [
    "__agents__",
    "DataAgent",
    "ChatAgent",
]
```

## Configuration

Settings in `runtime/settings.py`:

```python
# Plugin settings
enable_plugin_discovery: bool = True
plugin_root_dir: str = "plugins"
plugin_agents_dir: str = "agents"
plugin_tools_dir: str = "tools"
custom_agents_dir: str | None = None  # Optional custom directory
```

## API Access

Once loaded, plugins are available via the registry:

```python
from runtime.core.plugin.registry import get_plugin_registry

registry = get_plugin_registry()

# List all tools
tools = registry.list_tools()

# Get specific tool
tool_meta = registry.get_tool('my_tool')
tool_instance = tool_meta.class_obj()

# List all agents  
agents = registry.list_agents()

# Get specific agent
agent_meta = registry.get_agent('my-agent')
```

## Summary

The manifest-based plugin system provides:

- ✅ **Explicit Control**: Clear declaration of what's loaded
- ✅ **Easy Management**: Comment out to disable plugins
- ✅ **Load Order**: Predictable initialization sequence
- ✅ **Better Errors**: Import failures are caught early
- ✅ **IDE Support**: Auto-completion and type checking
- ✅ **Testability**: Easy to unit test individual plugins
- ✅ **Flexibility**: Support for multiple plugin directories

For questions or issues, check the logs at startup or refer to the validation error messages.

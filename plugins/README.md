## Plugin Development Guide

## Overview

This directory contains custom agents and tools that are registered via manifest files (`__init__.py`) and loaded by the runtime at startup.

## Directory Structure

```
plugins/
├── agents/                      # Custom agent templates
│   ├── __init__.py             # Agent manifest (registers agents)
│   ├── AGENT_DEVELOPMENT_GUIDE.md  # Complete agent development guide
│   ├── test_agent.py           # Example plugin agent
│   └── example_agent.py.template   # Template for new agents
├── tools/                       # Custom tools
│   ├── __init__.py             # Tool manifest (registers tools)
│   ├── file_tools.py           # File operation tools
│   ├── web_tools.py            # Web operation tools
│   └── example_tool.py.template    # Template for new tools
└── README.md                    # This file
```

## Quick Links

📚 **[Agent Development Guide](agents/AGENT_DEVELOPMENT_GUIDE.md)** - Complete guide for creating custom agents

🔧 **Plugin System Documentation**: See `docs/PLUGIN_SYSTEM.md` in project root

## Creating a Custom Agent

### Step 1: Create Your Agent File

Create a Python file in `plugins/agents/`:

```python
# plugins/agents/my_custom_agent.py
from pydantic import BaseModel, Field
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphChatAgent

class MyAgentConfig(BaseModel):
    temperature: float = Field(default=0.7)

class MyCustomAgent(BaseLangGraphChatAgent[MyAgentConfig]):
    """My custom agent for specific tasks."""
    
    # Required metadata
    template_id = "my-custom-agent"
    template_name = "My Custom Agent"
    template_version = "1.0.0"
    template_description = "Agent specialized for XYZ tasks"
    config_schema = MyAgentConfig
    
    async def _build_graph(self):
        """Build the agent graph."""
        # ... implement your graph
        pass
    
    def _create_initial_state(self, messages):
        return {"messages": self._convert_to_langgraph_messages(messages)}
    
    async def _extract_final_content(self, final_state):
        return final_state["messages"][-1].content
```

### Step 2: Register in Manifest

Edit `plugins/agents/__init__.py` to register your agent:

```python
from .my_custom_agent import MyCustomAgent
from .test_agent import TestPluginAgent

__agents__ = [
    TestPluginAgent,
    MyCustomAgent,  # Add your agent here
]
```

**That's it!** Your agent will be available on next startup.

📚 **For complete examples and patterns, see [AGENT_DEVELOPMENT_GUIDE.md](agents/AGENT_DEVELOPMENT_GUIDE.md)**

Usage:
```bash
./cli_tool.py agents create my-custom-agent --name "My Agent"
```

## Creating a Custom Tool

Create a Python file in `plugins/tools/` that inherits from `BaseTool`:

```python
# plugins/tools/my_search_tool.py

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class MySearchInput(BaseModel):
    """Input schema for my search tool."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, description="Maximum results to return")

class MySearchTool(BaseTool):
    """Custom search tool."""
    
    # Required attributes
    name: str = "my_search"
    description: str = "Search for information using custom search engine"
    args_schema: type[BaseModel] = MySearchInput
    
    # Optional: Plugin version
    __version__ = "1.0.0"
    
    def _run(self, query: str, max_results: int = 5) -> str:
        """Execute the search."""
        # Implement your search logic here
        results = f"Search results for '{query}' (top {max_results})"
        return results
    
    async def _arun(self, query: str, max_results: int = 5) -> str:
        """Async version (optional)."""
        return self._run(query, max_results)
```

### Step 2: Register in Manifest

Edit `plugins/tools/__init__.py` to register your tool:

```python
from .file_tools import ReadLinesTool, CreateFileTool
from .my_search_tool import MySearchTool

__tools__ = [
    ReadLinesTool,
    CreateFileTool,
    MySearchTool,  # Add your tool here
]
```

**That's it!** Your tool will be available on next startup.

### Using Your Tools

#### Method 1: Explicit Tool List (Recommended)
Configure specific tools in your toolset (`config/services-config.json`):
```json
{
  "toolsets": {
    "toolsets": {
      "my_toolset": {
        "type": "custom",
        "config": {
          "tools": ["read_lines", "fetch_url", "my_search"],
          "description": "Mix of built-in and custom tools"
        }
      }
    }
  }
}
```

### Method 2: Auto-Discover All Plugin Tools
Automatically load ALL plugin tools without listing them:
```json
{
  "toolsets": {
    "toolsets": {
      "all-plugins": {
        "type": "custom",
        "config": {
          "auto_discover_plugins": true,
          "description": "All tools from plugins/ directory"
        }
      }
    }
  }
}
```

**When to use each method:**
- **Explicit list**: Production, when you want precise control over which tools are available
- **Auto-discover**: Development, rapid prototyping, when agents need access to all custom tools

## Agent Requirements

Your agent class must:
1. Inherit from `BaseLangGraphAgent` or derived classes (`BaseLangGraphChatAgent`, etc.)
2. Define these class attributes:
   - `template_id` (str): Unique identifier (kebab-case recommended)
   - `template_name` (str): Human-readable name
   - `template_version` (str): Semantic version (e.g., "1.0.0")
   - `template_description` (str): Brief description
3. Implement `async def _build_graph(self)` method

## Tool Requirements

Your tool class must:
1. Inherit from `langchain_core.tools.BaseTool`
2. Define these class attributes:
   - `name` (str): Tool name (snake_case recommended)
   - `description` (str): What the tool does
   - `args_schema` (optional): Pydantic model for input validation
3. Implement `def _run(...)` method (sync execution)
4. Optionally implement `async def _arun(...)` method (async execution)
5. Be instantiable with zero arguments (no required constructor params)

## Configuration

Configure plugin directories in `.env`:

```bash
# Plugin root directory
PLUGIN_ROOT_DIR=plugins

# Subdirectories (relative to PLUGIN_ROOT_DIR)
PLUGIN_AGENTS_DIR=agents
PLUGIN_TOOLS_DIR=tools

# Optional: Use custom absolute directories
# CUSTOM_AGENTS_DIR=/path/to/my/agents
# CUSTOM_TOOLS_DIR=/path/to/my/tools

# Feature flag
ENABLE_PLUGIN_DISCOVERY=true
```

## Best Practices

1. **Naming Conventions**:
   - Agent template IDs: `kebab-case` (e.g., `my-custom-agent`)
   - Tool names: `snake_case` (e.g., `my_custom_tool`)
   - File names: descriptive, `snake_case` (e.g., `my_search_tool.py`)

2. **Documentation**:
   - Add clear docstrings to your classes
   - Document parameters and return types
   - Include usage examples in docstrings

3. **Error Handling**:
   - Handle exceptions gracefully in tool `_run()` methods
   - Return descriptive error messages
   - Log errors for debugging

4. **Testing**:
   - Test your plugins before deploying
   - Use the CLI to verify discovery: `./cli_tool.py templates list`
   - Test tool execution manually

5. **Dependencies**:
   - If your plugin requires extra packages, document them
   - Ensure dependencies are installed before using the plugin
   - Handle import errors gracefully

## Troubleshooting

**Plugin not discovered?**
- Check file name doesn't start with `_` (private modules are skipped)
- Verify class inherits from correct base class
- Check logs for import/validation errors
- Ensure required attributes are defined

**Naming collision?**
- Built-in agents/tools take precedence over plugins
- First discovered plugin wins if multiple have same ID
- Check logs for collision warnings

**Import errors?**
- Ensure all dependencies are installed
- Check Python path and module imports
- Review startup logs for detailed errors

## Testing Your Plugin

```bash
# 1. Verify plugin discovery (check logs)
python -m runtime.main

# 2. List discovered templates
./cli_tool.py templates list

# 3. Create agent from plugin
./cli_tool.py agents create my-custom-agent --name "Test Agent"

# 4. Test execution
./cli_tool.py chat <agent-id>
```

## Examples

See the template files in this directory:
- `agents/example_agent.py.template` - Example agent plugin
- `tools/example_tool.py.template` - Example tool plugin

Copy and modify these templates to create your own plugins!

## Security Notes

- Plugins execute with full system privileges
- Only load plugins from trusted sources
- Review plugin code before deployment
- In production, consider disabling plugin discovery or using custom directories with strict permissions

## Documentation

### Agent Development
- **[Agent Development Guide](agents/AGENT_DEVELOPMENT_GUIDE.md)** - Complete guide with examples, patterns, and best practices
- `agents/example_agent.py.template` - Quick-start template
- `agents/test_agent.py` - Working example agent

### Plugin System
- **`docs/PLUGIN_SYSTEM.md`** - Complete plugin system documentation
- **`docs/IMPLEMENTATION_SUMMARY.md`** - Architecture and implementation details

### Tools
- `tools/example_tool.py.template` - Quick-start template
- `tools/file_tools.py` - File operation tools (working examples)
- `tools/web_tools.py` - Web operation tools (working examples)

## Support

For detailed information:
- Agent development → `agents/AGENT_DEVELOPMENT_GUIDE.md`
- Plugin system → `docs/PLUGIN_SYSTEM.md`
- Built-in agents → `runtime/infrastructure/frameworks/langgraph/templates/`

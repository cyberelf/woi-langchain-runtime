# Agent CLI Examples

This directory contains examples demonstrating how to use the LangChain Runtime client SDK to interact with agents.

## Simple Agent CLI Example

The `simple_agent_cli.py` script provides an interactive command-line interface for working with agents from the runtime system.

### Features

- **Dynamic Agent Discovery**: Automatically discovers and lists all available agent templates (built-in + plugins)
- **Agent Selection**: Choose from any available agent template at runtime
- **Tool Selection**: Select which tools to enable for your agent (file operations, web tools, etc.)
- **Task Management**: Automatic task ID tracking for stateful conversations
- **Streaming Support**: Toggle between streaming and non-streaming responses
- **Interactive Commands**: Control conversation flow with simple commands
- **Context Preservation**: Maintain task and context IDs across messages
- **Agent Recreation**: Option to recreate existing agents with new configurations

### Prerequisites

1. Set up environment variables:
   ```bash
   export RUNTIME_BASE_URL="http://localhost:8000/v1/"
   export RUNTIME_TOKEN="your-token-here"
   export OPENAI_API_KEY="your-openai-key"  # or other LLM provider key
   ```

2. Start the runtime server:
   ```bash
   python scripts/start.py
   ```

### Usage

Run the example:
```bash
python examples/simple_agent_cli.py
```

The CLI will guide you through:
1. **Template Selection**: Choose from all available agent templates (built-in and plugins)
2. **Tool Selection**: Pick which tools to enable (file operations, web tools, or none)
3. **Agent Creation**: Automatically creates or reuses an existing agent
4. **Interactive Chat**: Start chatting with your configured agent

### Available Templates

The CLI automatically discovers all available templates from the runtime. Common templates include:

#### Built-in Templates

**1. Simple Test Agent** (`simple-test`)
- Basic conversational agent
- Configurable response prefix
- Good for testing and simple interactions

**2. Workflow Agent** (`langgraph-workflow`)
- Multi-step processing pipeline
- Configurable workflow steps
- Each step can have its own tools and timeout
- Supports retries and error handling

#### Plugin Templates

**3. Test Plugin Agent** (`test-plugin-agent`)
- Example plugin-based agent
- Demonstrates the plugin system
- Customizable greeting and iteration limits

*Additional templates may be available depending on installed plugins*

### Available Tools

The CLI allows you to select from the following tools:

| Tool | ID | Description |
|------|-----|-------------|
| Read Lines | `read-lines` | Read specific lines from files |
| Create File | `create-file` | Create new files with content |
| Grep File | `grep-file` | Search for patterns in files |
| Delete File | `delete-file` | Delete files |
| Fetch URL | `fetch-url` | Fetch content from URLs |
| Parse URL | `parse-url` | Parse and extract data from URLs |

**Note**: For workflow agents, tools are assigned to specific workflow steps.

### Interactive Commands

During a chat session, you can use the following commands:

| Command | Description |
|---------|-------------|
| `exit` | Exit the chat session |
| `stream` | Toggle between streaming and non-streaming mode |
| `clear` | Clear conversation history and reset task |
| `newtask` | Start a new task (resets task ID while keeping history) |

### Example Session

```
🚀 Agent CLI Example (using Client SDK, timeout=300.0s)
============================================================

📋 Available Templates:
  1. simple-test v1.0.0 (langgraph)
     A simple test agent for development and testing.
  2. langgraph-workflow v1.0.0 (langgraph)
     A workflow agent that processes tasks through multiple steps.
  3. test-plugin-agent v1.0.0 (langgraph)
     Test plugin agent demonstrating the plugin system

Found 3 template(s)

🔧 Select Agent Template:
Enter choice (1-3) [default: 1]: 1

🛠️  Available Tools:
  0. None (no tools)
  1. read-lines
  2. create-file
  3. grep-file
  4. delete-file
  5. fetch-url
  6. parse-url

Select tools to enable (comma-separated numbers, or 0 for none) [default: 0]: 
Tools: 1,5,6
✅ Enabled tools: read-lines, fetch-url, parse-url

🤖 Existing Agents:
  No existing agents found

🔧 Creating new Simple Test Cli Agent...
✅ Agent created: Simple Test Cli Agent

🎯 Agent Details:
   ID: simple-test-cli-example
   Name: Simple Test Cli Agent
   Template: simple-test v1.0.0
   Status: draft
   Tools: read-lines, fetch-url, parse-url

💬 Interactive Chat Session
Commands:
  'exit' - Exit the chat
  'stream' - Toggle streaming mode
  'clear' - Clear conversation history and reset task
  'newtask' - Start a new task (resets task ID)
============================================================

You: Hello! Can you help me fetch a URL?
Simple Test Cli Agent: 🤖 Of course! I can help you fetch URLs...
```

### Task Management

The example demonstrates proper task management for stateful conversations:

#### First Message
When you send your first message, the system automatically creates a task ID:
```
You: Hello, can you help me?
[📋 Task ID: abc123def456]
[🔗 Context ID: ctx789]
Agent: Hello! I'd be happy to help you...
```

#### Subsequent Messages
The same task ID is maintained across the conversation:
```
You: What can you do for me?
Agent: Based on our conversation...
```

#### Clearing Task
Use the `clear` command to reset both conversation history and task:
```
You: clear
🧹 Conversation history cleared and task reset
```

#### Starting New Task
Use the `newtask` command to start a fresh task while keeping conversation context:
```
You: newtask
🆕 Task reset - next message will start a new task
```

### Streaming vs Non-Streaming

#### Streaming Mode (Default: OFF)
Toggle with the `stream` command:
```
You: stream
🌊 Streaming mode: ON
```

In streaming mode, responses are displayed character by character as they arrive.

#### Non-Streaming Mode
Responses are returned as complete messages.

### Example Session

```
🚀 Agent CLI Example (using Client SDK)
============================================================

📋 Available Templates:
  • simple-test v1.0.0 (langgraph)
    Simple test agent for demonstrations
  • langgraph-workflow v1.0.0 (langgraph)
    Executes predefined workflows with multiple steps

Found 2 template(s)

🔧 Select Agent Type:
  1. Simple Test Agent
  2. Workflow Agent

Enter choice (1 or 2) [default: 1]: 2

🤖 Existing Agents:
  No existing agents found

🔧 Creating new Workflow CLI Agent...
✅ Agent created: Workflow CLI Agent

🎯 Agent Details:
   ID: workflow-example
   Name: Workflow CLI Agent
   Template: langgraph-workflow v1.0.0
   Status: draft

💬 Interactive Chat Session
Commands:
  'exit' - Exit the chat
  'stream' - Toggle streaming mode
  'clear' - Clear conversation history and reset task
  'newtask' - Start a new task (resets task ID)
============================================================

You: Can you help me write a Python function?
[📋 Task ID: wf_xyz123]
[🔗 Context ID: ctx_abc456]
Workflow CLI Agent: I'll help you write a Python function. First, let me analyze what you need...

You: Make it calculate fibonacci numbers
Workflow CLI Agent: Based on our discussion, here's a Python function to calculate Fibonacci numbers...

You: newtask
🆕 Task reset - next message will start a new task

You: What's the weather like?
[📋 Task ID: wf_xyz789]
Workflow CLI Agent: I'll help you with that. Let me process your weather request...

You: clear
🧹 Conversation history cleared and task reset

You: exit
👋 Goodbye!
```

### Code Structure

The example demonstrates:

1. **Client SDK Usage**: Using `RuntimeClientContext` for automatic resource management
2. **Agent Discovery**: Listing available templates
3. **Agent Creation**: Creating agents with different configurations
4. **Chat Execution**: Both streaming and non-streaming modes
5. **Metadata Handling**: Extracting and using task_id and context_id
6. **Error Handling**: Graceful error recovery

### Tips

- **Workflow Agents**: Best for multi-step tasks that need structured processing
- **Simple Agents**: Best for quick Q&A and conversational interfaces
- **Task IDs**: Useful for tracking conversations across sessions
- **Streaming**: Enable for real-time response feedback
- **Context IDs**: Help maintain conversation state in distributed systems

### Troubleshooting

**Issue**: "Authentication failed"
- **Solution**: Check your `RUNTIME_TOKEN` environment variable

**Issue**: "No templates available"
- **Solution**: Ensure the runtime server is running and templates are registered

**Issue**: "Agent creation failed"
- **Solution**: Verify your LLM configuration (e.g., `llm_config_id: "deepseek"`)

**Issue**: Workflow agent not working as expected
- **Solution**: Check the workflow step configuration and ensure prompts are clear

### Advanced Usage

#### Custom Workflow Steps

Modify the `template_config` in the code to customize workflow steps:

```python
template_config = {
    "steps": [
        {
            "name": "Step 1: Custom Step",
            "prompt": "Your custom prompt here",
            "tools": [],  # Add tool names if needed
            "timeout": 30,
            "retry_count": 1
        },
        # Add more steps...
    ],
    "max_retries": 2,
    "step_timeout": 60,
    "fail_on_error": False
}
```

#### Using Tools

Add tools to workflow steps:

```python
{
    "name": "Research Step",
    "prompt": "Research the topic using available tools",
    "tools": ["web_search", "calculator"],  # Available tools
    "timeout": 60,
    "retry_count": 2
}
```

## More Examples

Check the `/tests` directory for more examples:
- API integration tests: `tests/api/test_api.py`
- Workflow execution tests: `tests/integration/test_agent_execution.py`

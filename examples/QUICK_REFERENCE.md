# Quick Reference: Agent CLI with Task Management

## Quick Start

```bash
# Set environment
export RUNTIME_BASE_URL="http://localhost:8000/v1/"
export RUNTIME_TOKEN="your-token"
export OPENAI_API_KEY="your-key"

# Run example
python examples/simple_agent_cli.py
```

## Agent Types

### Simple Test Agent (Option 1)
- Single-turn conversations
- Quick Q&A
- Simple response formatting

### Workflow Agent (Option 2)
- Multi-step processing
- Step 1: Analyze Request
- Step 2: Generate Response
- Progress tracking

## Commands

| Command | Action |
|---------|--------|
| `exit` | Exit chat |
| `stream` | Toggle streaming ON/OFF |
| `clear` | Reset everything (history + task + context) |
| `newtask` | Reset task ID (keep history) |

## Task Management Patterns

### Pattern 1: Continuous Conversation
```
You: First question
[📋 Task ID: abc123]
Agent: Answer 1

You: Follow-up question
Agent: Answer 2 (same task)
```

### Pattern 2: Reset Everything
```
You: clear
🧹 Conversation history cleared and task reset

You: New topic
[📋 Task ID: xyz789]  # New task
Agent: Fresh response
```

### Pattern 3: New Task, Keep History
```
You: newtask
🆕 Task reset

You: Next question
[📋 Task ID: def456]  # New task
Agent: Response with prior context
```

## Metadata Flow

### First Message
```
Request:
  messages: [user_message]
  metadata: {}  # Empty

Response:
  content: "..."
  metadata: {
    "task_id": "wf_abc123",
    "context_id": "ctx_xyz"
  }
```

### Subsequent Messages
```
Request:
  messages: [history]
  metadata: {
    "task_id": "wf_abc123",    # From first response
    "context_id": "ctx_xyz"
  }

Response:
  content: "..."
  metadata: {
    "task_id": "wf_abc123",    # Same task
    "context_id": "ctx_xyz"
  }
```

## Streaming vs Non-Streaming

### Streaming (Character-by-Character)
```python
stream = client.stream_chat_with_agent(
    agent_id, 
    messages,
    metadata={"task_id": task_id}
)

async for chunk in stream:
    # First chunk contains task_id
    if chunk.metadata:
        task_id = chunk.metadata.get('task_id')
    
    # Display content
    print(chunk.choices[0].delta.content)
```

### Non-Streaming (Complete Message)
```python
response = await client.chat_with_agent(
    agent_id,
    messages,
    metadata={"task_id": task_id}
)

# Extract task_id
task_id = response.metadata.get('task_id')

# Display response
print(response.choices[0].message.content)
```

## Workflow Steps Configuration

```python
"template_config": {
    "steps": [
        {
            "name": "Step Name",
            "prompt": "What to do in this step",
            "tools": [],           # Optional tool list
            "timeout": 30,         # Seconds
            "retry_count": 1       # Number of retries
        }
    ],
    "max_retries": 2,              # Max retries per step
    "step_timeout": 60,            # Default timeout
    "fail_on_error": False         # Continue on failure
}
```

## Common Issues & Solutions

### Issue: No task_id returned
**Cause**: First message in new conversation
**Solution**: Normal - task_id created on first response

### Issue: task_id changes unexpectedly
**Cause**: Used `clear` or `newtask` command
**Solution**: Intended behavior for task reset

### Issue: Workflow not executing steps
**Cause**: Invalid step configuration
**Solution**: Check step names, prompts, and dependencies

### Issue: Streaming not showing task_id
**Cause**: Metadata not in first chunk
**Solution**: Check server logs, ensure metadata is included

## Code Snippets

### Create Workflow Agent
```python
agent_data = CreateAgentRequest(
    id="my-workflow",
    name="My Workflow Agent",
    template_id="langgraph-workflow",
    template_version_id="1.0.0",
    template_config={
        "steps": [...],
        "max_retries": 2,
        "step_timeout": 60,
        "fail_on_error": False
    },
    system_prompt="You are a helpful assistant",
    llm_config_id="deepseek"
)
```

### Send Message with Task
```python
metadata = {}
if task_id:
    metadata["task_id"] = task_id
if context_id:
    metadata["context_id"] = context_id

response = await client.chat_with_agent(
    agent_id,
    messages,
    metadata=metadata if metadata else None
)
```

### Extract Task ID
```python
# From response
if hasattr(response, 'metadata') and response.metadata:
    task_id = response.metadata.get('task_id')
    context_id = response.metadata.get('context_id')

# From streaming chunk
if chunk.metadata:
    task_id = chunk.metadata.get('task_id')
    context_id = chunk.metadata.get('context_id')
```

## Visual Indicators

- 📋 Task ID displayed
- 🔗 Context ID displayed
- 🧹 History cleared
- 🆕 New task started
- 🌊 Streaming mode changed
- 👋 Exiting application
- ✅ Success action
- ❌ Error occurred

## Best Practices

1. **Always extract task_id from first response**
   - Check both streaming chunks and complete responses
   - Store for subsequent messages

2. **Use `clear` for complete reset**
   - New topic
   - Starting over
   - Clearing sensitive data

3. **Use `newtask` for context switch**
   - Keep conversation context
   - Start new task tracking
   - Switch between related topics

4. **Enable streaming for long responses**
   - Better user experience
   - Real-time feedback
   - Early error detection

5. **Monitor task_id changes**
   - Helps debug conversation flow
   - Tracks task boundaries
   - Useful for logging

## Environment Variables

```bash
# Required
RUNTIME_BASE_URL="http://localhost:8000/v1/"
RUNTIME_TOKEN="your-runtime-token"

# LLM Provider (choose one)
OPENAI_API_KEY="your-openai-key"
ANTHROPIC_API_KEY="your-anthropic-key"
# ... or other provider

# Optional
LOG_LEVEL="INFO"
```

## Files Reference

- `examples/simple_agent_cli.py` - Main example code
- `examples/README.md` - Full documentation
- `examples/TASK_MANAGEMENT_FLOW.md` - Flow diagrams
- `client_sdk/models.py` - Data models
- `client_sdk/client.py` - Client implementation

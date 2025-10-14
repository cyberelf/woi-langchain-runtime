# Quick Reference: LangGraph Agent Base Classes

## At a Glance

```
BaseLangGraphAgent        ← DON'T inherit directly
├── BaseLangGraphChatAgent    ← For chat/conversational agents
└── BaseLangGraphTaskAgent    ← For task/workflow agents
```

## Quick Decision Tree

```
Is your agent primarily conversational?
├── YES → Use BaseLangGraphChatAgent
│   └── Users see responses as they're typed (like ChatGPT)
│
└── NO → Is it a multi-step workflow?
    ├── YES → Use BaseLangGraphTaskAgent
    │   └── You control exactly what users see
    │
    └── UNSURE → Does it use tools/reasoning that should be visible?
        ├── YES → BaseLangGraphChatAgent
        └── NO → BaseLangGraphTaskAgent
```

## Minimal Templates

### Chat Agent (Minimal)
```python
from pydantic import BaseModel, Field
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphChatAgent

class MyConfig(BaseModel):
    temperature: float = Field(default=0.7)

class MyChatAgent(BaseLangGraphChatAgent[MyConfig]):
    template_name = "My Chat Agent"
    template_id = "my-chat"
    template_version = "1.0.0"
    template_description = "A chat agent"
    config_schema = MyConfig
    
    async def _build_graph(self):
        # Build your graph
        ...
    
    def _create_initial_state(self, messages):
        return {"messages": self._convert_to_langgraph_messages(messages)}
    
    async def _extract_final_content(self, final_state):
        return final_state["messages"][-1].content
```

### Task Agent (Minimal)
```python
from pydantic import BaseModel, Field
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphTaskAgent

class MyConfig(BaseModel):
    max_steps: int = Field(default=5)

class MyTaskAgent(BaseLangGraphTaskAgent[MyConfig]):
    template_name = "My Task Agent"
    template_id = "my-task"
    template_version = "1.0.0"
    template_description = "A task agent"
    config_schema = MyConfig
    
    async def _build_graph(self):
        # Build your graph
        ...
    
    def _create_initial_state(self, messages):
        return {
            "messages": self._convert_to_langgraph_messages(messages),
            "results": []
        }
    
    async def _extract_final_content(self, final_state):
        return final_state.get("final_result", "")
    
    async def _process_state_update(self, state_update, chunk_index, metadata):
        # THIS METHOD IS REQUIRED for task agents!
        for node_name, node_state in state_update.items():
            if node_name == "important_node":
                yield StreamingChunk(content="...", finish_reason=None, metadata={})
```

## Method Comparison

| Method | BaseLangGraphChatAgent | BaseLangGraphTaskAgent |
|--------|----------------------|----------------------|
| `_build_graph()` | ✅ Required | ✅ Required |
| `_create_initial_state()` | ✅ Required | ✅ Required |
| `_extract_final_content()` | ✅ Required | ✅ Required |
| `_process_message_chunk()` | ⚙️ Optional (has default) | ❌ N/A |
| `_process_state_update()` | ❌ N/A | ✅ Required |

## Streaming Behavior

### Chat Agent Streaming
```python
# Streams: Individual tokens/chunks as LLM generates
agent = MyChatAgent(...)
async for chunk in agent.stream_execute(messages):
    print(chunk.content, end='')  # "Hello", " how", " are", " you?"
```

### Task Agent Streaming
```python
# Streams: Only what you decide to show
agent = MyTaskAgent(...)
async for chunk in agent.stream_execute(messages):
    print(chunk.content)
# Output:
# "📋 Planning complete"
# "✓ Step 1 done"
# "✓ Step 2 done"
# (internal validation is hidden)
```

## Common Patterns

### Chat: Add Tool Call Indicators
```python
class MyAgent(BaseLangGraphChatAgent[MyConfig]):
    async def _process_message_chunk(self, message, chunk_index, metadata):
        if hasattr(message, 'tool_calls') and message.tool_calls:
            yield StreamingChunk(content=f"[Using tool: {message.tool_calls[0]['name']}]\n", ...)
        
        if message.content:
            yield StreamingChunk(content=message.content, ...)
```

### Task: Stream Phase Progress
```python
class MyAgent(BaseLangGraphTaskAgent[MyConfig]):
    async def _process_state_update(self, state_update, chunk_index, metadata):
        for node_name, node_state in state_update.items():
            if node_name == "planning":
                yield StreamingChunk(content="📋 Planning...\n", ...)
            elif node_name == "execution":
                yield StreamingChunk(content="⚙️ Executing...\n", ...)
            # Skip internal nodes by not yielding
```

## Helper Methods (Available in All Base Classes)

```python
# Message conversion
langgraph_messages = self._convert_to_langgraph_messages(chat_messages)
chat_message = self._convert_from_langgraph_message(base_message)

# Client access
llm_client = self._get_llm_client(temperature=0.5, max_tokens=100)
toolset_client = self._get_toolset_client()

# Graph management
graph = await self.get_graph()  # Cached after first call

# Access configuration
self.config.temperature  # Your Pydantic config
self.system_prompt       # System prompt string
self.llm_client          # Default LLM client
self.toolset_client      # Tools client (if configured)
```

## Import Paths

```python
# Base classes
from runtime.infrastructure.frameworks.langgraph.templates.base import (
    BaseLangGraphChatAgent,
    BaseLangGraphTaskAgent,
)

# Domain objects
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.core.executors import ExecutionResult, StreamingChunk

# LangGraph
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

# Pydantic
from pydantic import BaseModel, Field
```

## Common Mistakes to Avoid

❌ **DON'T:**
```python
class MyAgent(BaseLangGraphAgent[MyConfig]):  # ← Wrong! Don't inherit from base directly
    ...
```

❌ **DON'T:**
```python
class MyTaskAgent(BaseLangGraphTaskAgent[MyConfig]):
    # Forgot to implement _process_state_update() ← Will fail!
    pass
```

❌ **DON'T:**
```python
class MyChatAgent(BaseLangGraphChatAgent[MyConfig]):
    async def _process_state_update(self, ...):  # ← Wrong method for chat agents!
        ...
```

✅ **DO:**
```python
class MyChatAgent(BaseLangGraphChatAgent[MyConfig]):  # ← Correct!
    async def _build_graph(self): ...
    def _create_initial_state(self, messages): ...
    async def _extract_final_content(self, final_state): ...
    # Optionally override _process_message_chunk()
```

✅ **DO:**
```python
class MyTaskAgent(BaseLangGraphTaskAgent[MyConfig]):  # ← Correct!
    async def _build_graph(self): ...
    def _create_initial_state(self, messages): ...
    async def _extract_final_content(self, final_state): ...
    async def _process_state_update(self, state_update, ...):  # ← Required!
        ...
```

## Testing

```python
import pytest
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole

@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent(config, llm_service)
    messages = [ChatMessage(role=MessageRole.USER, content="Hello")]
    
    # Test non-streaming
    result = await agent.execute(messages)
    assert result.success
    assert result.message
    
    # Test streaming
    chunks = []
    async for chunk in agent.stream_execute(messages):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert chunks[-1].finish_reason == "stop"
```

## Documentation Links

- **Full Guide**: `TEMPLATES_GUIDE.md` - Comprehensive tutorial with examples
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md` - Architecture explanation
- **Examples**: 
  - `examples/simple_chat_example.py` - Complete chat agent
  - `examples/task_agent_example.py` - Complete task agent

## Need Help?

1. Check `TEMPLATES_GUIDE.md` for detailed examples
2. Look at `simple.py` (chat) and `workflow.py` (task) for real implementations
3. Review the docstrings in `base.py` - they're comprehensive!

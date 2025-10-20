# LangGraph Agent Development Guide

Complete guide for creating custom LangGraph agent templates.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Choosing the Right Base Class](#choosing-the-right-base-class)
3. [Quick Reference](#quick-reference)
4. [BaseLangGraphChatAgent](#baselanggraphchatagent)
5. [BaseLangGraphTaskAgent](#baselanggraphtaskagent)
6. [Common Patterns](#common-patterns)
7. [Complete Examples](#complete-examples)
8. [Best Practices](#best-practices)
9. [Testing](#testing)

---

## Quick Start

### Decision Tree

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

### Minimal Templates

#### Chat Agent (30 seconds)
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
        # Build your graph here
        ...
    
    def _create_initial_state(self, messages):
        return {"messages": self._convert_to_langgraph_messages(messages)}
    
    async def _extract_final_content(self, final_state):
        return final_state["messages"][-1].content
```

#### Task Agent (30 seconds)
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
                yield StreamingChunk(content="Progress...", finish_reason=None, metadata={})
```

---

## Choosing the Right Base Class

### Base Class Hierarchy

```
BaseLangGraphAgent        ← DON'T inherit directly
├── BaseLangGraphChatAgent    ← For chat/conversational agents
└── BaseLangGraphTaskAgent    ← For task/workflow agents
```

### Use `BaseLangGraphChatAgent` when:

✅ Building a conversational chatbot  
✅ Users expect to see responses as they're being typed (like ChatGPT)  
✅ Real-time feedback improves user experience  
✅ Tool calls and reasoning should be visible  
✅ Agent is primarily focused on chat interactions  

### Use `BaseLangGraphTaskAgent` when:

✅ Building a multi-step workflow or automation agent  
✅ You want to hide internal reasoning and show only results  
✅ Agent has complex state machines with many intermediate steps  
✅ You want fine-grained control over what users see  
✅ Agent performs planning, execution, and validation phases  

---

## Quick Reference

### Method Comparison

| Method | BaseLangGraphChatAgent | BaseLangGraphTaskAgent |
|--------|----------------------|----------------------|
| `_build_graph()` | ✅ Required | ✅ Required |
| `_create_initial_state()` | ✅ Required | ✅ Required |
| `_extract_final_content()` | ✅ Required | ✅ Required |
| `_process_message_chunk()` | ⚙️ Optional (has default) | ❌ N/A |
| `_process_state_update()` | ❌ N/A | ✅ Required |

### Streaming Behavior

**Chat Agent Streaming**
```python
# Streams: Individual tokens/chunks as LLM generates
agent = MyChatAgent(...)
async for chunk in agent.stream_execute(messages):
    print(chunk.content, end='')  # "Hello", " how", " are", " you?"
```

**Task Agent Streaming**
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

### Helper Methods (Available in All Base Classes)

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

### Common Import Paths

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
from typing import TypedDict, Literal
```

---

## BaseLangGraphChatAgent

### Full Structure

```python
from typing import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END

# 1. Define your configuration schema
class MyChatAgentConfig(BaseModel):
    """Configuration for my chat agent."""
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_iterations: int = Field(default=5, description="Max reasoning iterations")

# 2. Define state if needed
class ChatState(TypedDict):
    messages: list[BaseMessage]

# 3. Define your agent class
class MyChatAgent(BaseLangGraphChatAgent[MyChatAgentConfig]):
    """A conversational agent template."""
    
    # Template metadata (REQUIRED)
    template_name = "My Chat Agent"
    template_id = "my-chat-agent"
    template_version = "1.0.0"
    template_description = "A friendly conversational assistant"
    config_schema = MyChatAgentConfig
    
    # 4. Implement required methods
    async def _build_graph(self):
        """Build the LangGraph execution graph."""
        workflow = StateGraph(ChatState)
        workflow.add_node("chat", self._chat_node)
        workflow.set_entry_point("chat")
        workflow.set_finish_point("chat")
        return workflow.compile()
    
    async def _chat_node(self, state):
        """Chat node implementation."""
        response = await self.llm_client.ainvoke(state["messages"])
        return {"messages": [response]}
    
    def _create_initial_state(self, messages):
        """Convert input messages to graph state."""
        langgraph_messages = self._convert_to_langgraph_messages(messages)
        if self.system_prompt:
            system_msg = SystemMessage(content=self.system_prompt)
            langgraph_messages = [system_msg] + langgraph_messages
        return {"messages": langgraph_messages}
    
    async def _extract_final_content(self, final_state):
        """Extract final response from state."""
        messages = final_state.get("messages", [])
        return messages[-1].content if messages else ""
```

### Customizing Message Streaming

Chat agents automatically stream all message chunks. Customize if needed:

```python
class MyChatAgent(BaseLangGraphChatAgent[MyChatAgentConfig]):
    # ... other methods ...
    
    async def _process_message_chunk(self, message, chunk_index, metadata):
        """Custom chunk processing."""
        
        # Skip empty chunks
        if not hasattr(message, 'content') or not message.content:
            return
        
        # Add indicators for tool calls
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_name = message.tool_calls[0].get('name', 'unknown')
            yield StreamingChunk(
                content=f"🔧 Using {tool_name}...\n",
                finish_reason=None,
                metadata={'chunk_index': chunk_index, 'type': 'tool_indicator'}
            )
        
        # Stream the actual content
        if message.content:
            yield StreamingChunk(
                content=str(message.content),
                finish_reason=None,
                metadata={'chunk_index': chunk_index}
            )
```

---

## BaseLangGraphTaskAgent

### Full Structure

```python
from pydantic import BaseModel, Field
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphTaskAgent

# 1. Define your configuration schema
class MyTaskAgentConfig(BaseModel):
    """Configuration for my task agent."""
    max_planning_steps: int = Field(default=3, description="Max planning iterations")
    enable_validation: bool = Field(default=True, description="Validate results")

# 2. Define state
class WorkflowState(TypedDict):
    messages: list[BaseMessage]
    plan: list[str]
    current_step: int
    results: list[str]
    final_result: str

# 3. Define your agent class
class MyTaskAgent(BaseLangGraphTaskAgent[MyTaskAgentConfig]):
    """A task-oriented agent template."""
    
    # Template metadata (REQUIRED)
    template_name = "My Task Agent"
    template_id = "my-task-agent"
    template_version = "1.0.0"
    template_description = "Executes multi-step workflows"
    config_schema = MyTaskAgentConfig
    
    # 4. Implement required methods
    async def _build_graph(self):
        """Build the LangGraph execution graph."""
        workflow = StateGraph(WorkflowState)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("validate", self._validate_node)
        
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "execute")
        workflow.add_conditional_edges(
            "execute",
            self._should_continue,
            {"continue": "execute", "validate": "validate", "end": END}
        )
        workflow.add_edge("validate", END)
        
        return workflow.compile()
    
    def _create_initial_state(self, messages):
        """Convert input messages to graph state."""
        return {
            "messages": self._convert_to_langgraph_messages(messages),
            "plan": [],
            "current_step": 0,
            "results": [],
            "final_result": ""
        }
    
    async def _extract_final_content(self, final_state):
        """Extract final response from state."""
        return final_state.get("final_result", "")
    
    # 5. REQUIRED: Implement state update processing
    async def _process_state_update(self, state_update, chunk_index, metadata):
        """Process state updates and stream significant changes."""
        
        # state_update is a dict: {node_name: node_output_state}
        for node_name, node_state in state_update.items():
            
            if node_name == "plan":
                plan = node_state.get("plan", [])
                if plan:
                    yield StreamingChunk(
                        content=f"📋 Created plan with {len(plan)} steps\n",
                        finish_reason=None,
                        metadata={'phase': 'planning', 'node': node_name}
                    )
            
            elif node_name == "execute":
                current = node_state.get("current_step", 0)
                total = len(node_state.get("plan", []))
                yield StreamingChunk(
                    content=f"⚙️ Executing step {current + 1}/{total}\n",
                    finish_reason=None,
                    metadata={'phase': 'execution', 'node': node_name}
                )
            
            elif node_name == "validate":
                is_valid = node_state.get("is_valid", False)
                status = "✓" if is_valid else "⚠"
                yield StreamingChunk(
                    content=f"{status} Validation complete\n",
                    finish_reason=None,
                    metadata={'phase': 'validation', 'node': node_name}
                )
            
            # Internal nodes can be skipped by not yielding
    
    # Node implementations
    async def _plan_node(self, state):
        """Create execution plan."""
        # ... planning logic
        return {"plan": ["step1", "step2", "step3"]}
    
    async def _execute_node(self, state):
        """Execute current step."""
        # ... execution logic
        return {"current_step": state["current_step"] + 1}
    
    async def _validate_node(self, state):
        """Validate results."""
        # ... validation logic
        return {"final_result": "Success!", "is_valid": True}
    
    def _should_continue(self, state):
        """Routing logic."""
        if state["current_step"] >= len(state["plan"]):
            return "validate"
        return "continue"
```

### Controlling Streaming Output

The key to task agents is selective streaming:

```python
async def _process_state_update(self, state_update, chunk_index, metadata):
    """Stream only user-facing updates."""
    
    for node_name, node_state in state_update.items():
        
        # Stream public nodes
        if node_name in ["research", "analyze", "summarize"]:
            content = node_state.get("output", "")
            if content:
                yield StreamingChunk(
                    content=f"📊 {node_name.title()}: {content}\n",
                    finish_reason=None,
                    metadata={'node': node_name}
                )
        
        # Hide internal nodes (don't yield anything)
        elif node_name in ["_routing", "_validation", "_error_check"]:
            # Skip these - users don't need to see them
            pass
        
        # Add progress indicators
        elif node_name == "long_task":
            progress = node_state.get("progress", 0)
            yield StreamingChunk(
                content=f"Progress: {progress}%\n",
                finish_reason=None,
                metadata={'node': node_name, 'progress': progress}
            )
```

---

## Common Patterns

### Pattern 1: ReAct Agent (Chat-based)

```python
from langgraph.prebuilt import ToolNode

class ReActAgent(BaseLangGraphChatAgent[ReActConfig]):
    """ReAct agent with tool calling."""
    
    async def _build_graph(self):
        workflow = StateGraph(MessagesState)
        
        # Get tools
        tools = await self.toolset_client.tools if self.toolset_client else []
        llm_with_tools = self.llm_client.bind_tools(tools)
        
        # Add nodes
        workflow.add_node("agent", llm_with_tools)
        workflow.add_node("tools", ToolNode(tools))
        
        # Add edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "end": END}
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def _should_continue(self, state):
        """Check if should continue to tools."""
        messages = state["messages"]
        last_message = messages[-1]
        
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"
        return "end"
```

### Pattern 2: Planning Agent (Task-based)

```python
class PlanningAgent(BaseLangGraphTaskAgent[PlanningConfig]):
    """Agent that plans and executes in phases."""
    
    async def _build_graph(self):
        workflow = StateGraph(PlannerState)
        
        workflow.add_node("understand", self._understand_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("review", self._review_node)
        
        workflow.set_entry_point("understand")
        workflow.add_edge("understand", "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_conditional_edges(
            "execute",
            self._check_completion,
            {"complete": "review", "continue": "plan"}
        )
        workflow.add_edge("review", END)
        
        return workflow.compile()
    
    async def _process_state_update(self, state_update, chunk_index, metadata):
        """Stream progress through planning phases."""
        
        phase_emoji = {
            "understand": "🔍",
            "plan": "📋",
            "execute": "⚙️",
            "review": "✓"
        }
        
        for node_name, node_state in state_update.items():
            emoji = phase_emoji.get(node_name, "•")
            
            if node_name == "understand":
                requirements = node_state.get("requirements", [])
                yield StreamingChunk(
                    content=f"{emoji} Analyzing: {len(requirements)} requirements\n",
                    finish_reason=None,
                    metadata={'phase': node_name}
                )
            
            elif node_name == "plan":
                steps = node_state.get("steps", [])
                yield StreamingChunk(
                    content=f"{emoji} Planning: {len(steps)} steps\n",
                    finish_reason=None,
                    metadata={'phase': node_name}
                )
            
            elif node_name == "execute":
                current_step = node_state.get("current_step", "")
                yield StreamingChunk(
                    content=f"{emoji} Executing: {current_step}\n",
                    finish_reason=None,
                    metadata={'phase': node_name}
                )
            
            elif node_name == "review":
                yield StreamingChunk(
                    content=f"{emoji} Review complete\n",
                    finish_reason=None,
                    metadata={'phase': node_name}
                )
```

### Pattern 3: Tool-Calling Chat Agent with Indicators

```python
class ToolChatAgent(BaseLangGraphChatAgent[ToolConfig]):
    """Chat agent with visible tool usage."""
    
    async def _process_message_chunk(self, message, chunk_index, metadata):
        """Show tool calls to users."""
        
        # Show tool usage
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.get('name', 'unknown')
                yield StreamingChunk(
                    content=f"🔧 Using {tool_name}...\n",
                    finish_reason=None,
                    metadata={'type': 'tool_call', 'tool': tool_name}
                )
        
        # Show thinking/reasoning
        if hasattr(message, 'content') and message.content:
            # Add prefix for AI reasoning
            if isinstance(message, AIMessage):
                yield StreamingChunk(
                    content="💭 ",
                    finish_reason=None,
                    metadata={'type': 'thinking_prefix'}
                )
            
            # Stream content
            yield StreamingChunk(
                content=str(message.content),
                finish_reason=None,
                metadata={'type': 'content'}
            )
```

---

## Complete Examples

### Example 1: Simple Q&A Agent

```python
from typing import TypedDict
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END

class QAConfig(BaseModel):
    """Q&A agent configuration."""
    pass  # No custom config needed

class QAState(TypedDict):
    messages: list[BaseMessage]

class QAAgent(BaseLangGraphChatAgent[QAConfig]):
    """Simple question-answering agent."""
    
    template_name = "Q&A Agent"
    template_id = "qa-agent"
    template_version = "1.0.0"
    template_description = "Answers questions concisely"
    config_schema = QAConfig
    
    async def _build_graph(self):
        workflow = StateGraph(QAState)
        workflow.add_node("answer", self._answer_node)
        workflow.set_entry_point("answer")
        workflow.set_finish_point("answer")
        return workflow.compile()
    
    async def _answer_node(self, state):
        """Generate answer."""
        response = await self.llm_client.ainvoke(state["messages"])
        return {"messages": [response]}
    
    def _create_initial_state(self, messages):
        langgraph_messages = self._convert_to_langgraph_messages(messages)
        system_msg = SystemMessage(
            content="You are a helpful assistant. Provide concise, accurate answers."
        )
        return {"messages": [system_msg] + langgraph_messages}
    
    async def _extract_final_content(self, final_state):
        return final_state["messages"][-1].content
```

### Example 2: Research and Summarization Agent

```python
from typing import TypedDict, Literal
from pydantic import BaseModel, Field

class ResearchConfig(BaseModel):
    """Research agent configuration."""
    max_sources: int = Field(default=3, description="Max sources to research")
    summary_length: Literal["short", "medium", "long"] = Field(default="medium")

class ResearchState(TypedDict):
    messages: list[BaseMessage]
    topic: str
    sources: list[str]
    summaries: list[str]
    final_report: str

class ResearchAgent(BaseLangGraphTaskAgent[ResearchConfig]):
    """Agent that researches topics and creates reports."""
    
    template_name = "Research Agent"
    template_id = "research-agent"
    template_version = "1.0.0"
    template_description = "Researches topics and generates reports"
    config_schema = ResearchConfig
    
    async def _build_graph(self):
        workflow = StateGraph(ResearchState)
        
        workflow.add_node("extract_topic", self._extract_topic)
        workflow.add_node("research", self._research)
        workflow.add_node("summarize", self._summarize)
        workflow.add_node("compile_report", self._compile_report)
        
        workflow.set_entry_point("extract_topic")
        workflow.add_edge("extract_topic", "research")
        workflow.add_edge("research", "summarize")
        workflow.add_edge("summarize", "compile_report")
        workflow.add_edge("compile_report", END)
        
        return workflow.compile()
    
    def _create_initial_state(self, messages):
        return {
            "messages": self._convert_to_langgraph_messages(messages),
            "topic": "",
            "sources": [],
            "summaries": [],
            "final_report": ""
        }
    
    async def _extract_final_content(self, final_state):
        return final_state.get("final_report", "")
    
    async def _process_state_update(self, state_update, chunk_index, metadata):
        """Stream research progress."""
        
        for node_name, node_state in state_update.items():
            
            if node_name == "extract_topic":
                topic = node_state.get("topic", "")
                yield StreamingChunk(
                    content=f"🔍 Topic: {topic}\n",
                    finish_reason=None,
                    metadata={'phase': 'extraction'}
                )
            
            elif node_name == "research":
                sources = node_state.get("sources", [])
                yield StreamingChunk(
                    content=f"📚 Found {len(sources)} sources\n",
                    finish_reason=None,
                    metadata={'phase': 'research'}
                )
            
            elif node_name == "summarize":
                summaries = node_state.get("summaries", [])
                yield StreamingChunk(
                    content=f"📝 Summarized {len(summaries)} sources\n",
                    finish_reason=None,
                    metadata={'phase': 'summarization'}
                )
            
            elif node_name == "compile_report":
                yield StreamingChunk(
                    content="✓ Report complete\n",
                    finish_reason=None,
                    metadata={'phase': 'compilation'}
                )
    
    # Node implementations
    async def _extract_topic(self, state):
        """Extract research topic from user message."""
        messages = state["messages"]
        # Use LLM to extract topic
        topic = "extracted topic"  # Simplified
        return {"topic": topic}
    
    async def _research(self, state):
        """Research the topic."""
        # Use tools to find sources
        sources = ["source1", "source2", "source3"]  # Simplified
        return {"sources": sources[:self.config.max_sources]}
    
    async def _summarize(self, state):
        """Summarize each source."""
        # Use LLM to summarize
        summaries = ["summary1", "summary2"]  # Simplified
        return {"summaries": summaries}
    
    async def _compile_report(self, state):
        """Compile final report."""
        # Use LLM to create cohesive report
        report = f"Research report on {state['topic']}"  # Simplified
        return {"final_report": report}
```

---

## Best Practices

### 1. Configuration Design

```python
class GoodConfig(BaseModel):
    """Well-designed configuration."""
    
    # Use descriptive names
    max_reasoning_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of reasoning iterations"
    )
    
    # Include validation
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for response generation"
    )
    
    # Use enums for fixed choices
    response_style: Literal["concise", "detailed", "technical"] = Field(
        default="detailed",
        description="Style of response generation"
    )
    
    # Group related settings
    enable_web_search: bool = Field(default=True, description="Allow web searches")
    max_search_results: int = Field(default=5, description="Max search results")
```

### 2. Error Handling

```python
async def _build_graph(self):
    """Build graph with error handling."""
    try:
        workflow = StateGraph(MyState)
        # ... build graph
        return workflow.compile()
    except Exception as e:
        logger.error(f"Failed to build graph: {e}")
        raise

async def _my_node(self, state):
    """Node with error handling."""
    try:
        result = await self.llm_client.ainvoke(state["messages"])
        return {"result": result}
    except Exception as e:
        logger.error(f"Node execution failed: {e}")
        return {"error": str(e)}
```

### 3. Logging

```python
import logging

logger = logging.getLogger(__name__)

async def _process_state_update(self, state_update, chunk_index, metadata):
    """Process updates with logging."""
    logger.debug(f"Processing update #{chunk_index}: {list(state_update.keys())}")
    
    for node_name, node_state in state_update.items():
        logger.debug(f"Node {node_name} output: {node_state.keys()}")
        # ... process
```

### 4. Documentation

```python
class MyAgent(BaseLangGraphChatAgent[MyConfig]):
    """
    My Custom Agent - A specialized assistant for domain-specific tasks.
    
    This agent is designed for:
    - Task A: Description
    - Task B: Description
    - Task C: Description
    
    It uses a reasoning approach with tool integration.
    
    Configuration:
        temperature: Controls response randomness (0.0 - 2.0)
        max_iterations: Maximum reasoning steps (1 - 20)
    
    Example:
        ```python
        config = MyConfig(temperature=0.7)
        agent = MyAgent(config, llm_service)
        result = await agent.execute(messages)
        ```
    
    Limitations:
        - Cannot handle documents >10k tokens
        - Requires internet for API calls
        - Best suited for English language inputs
    """
```

---

## Testing

### Unit Tests

```python
import pytest
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole

@pytest.mark.asyncio
async def test_agent_execution():
    """Test basic agent execution."""
    config = MyConfig(temperature=0.7)
    agent = MyAgent(config, llm_service)
    
    messages = [ChatMessage(role=MessageRole.USER, content="Hello")]
    result = await agent.execute(messages)
    
    assert result.success
    assert result.message
    assert len(result.message.content) > 0

@pytest.mark.asyncio
async def test_agent_streaming():
    """Test agent streaming."""
    config = MyConfig(temperature=0.7)
    agent = MyAgent(config, llm_service)
    
    messages = [ChatMessage(role=MessageRole.USER, content="Hello")]
    
    chunks = []
    async for chunk in agent.stream_execute(messages):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert chunks[-1].finish_reason == "stop"

@pytest.mark.asyncio
async def test_agent_configuration():
    """Test configuration handling."""
    config = MyConfig(
        temperature=0.9,
        max_iterations=10
    )
    agent = MyAgent(config, llm_service)
    
    assert agent.config.temperature == 0.9
    assert agent.config.max_iterations == 10
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_agent_with_tools():
    """Test agent using tools."""
    config = MyConfig()
    agent = MyAgent(config, llm_service, toolset_service)
    
    messages = [
        ChatMessage(role=MessageRole.USER, content="Search for Python tutorials")
    ]
    
    result = await agent.execute(messages)
    assert result.success
    # Verify tool was called
```

---

## Common Mistakes to Avoid

❌ **DON'T inherit from BaseLangGraphAgent directly**
```python
class MyAgent(BaseLangGraphAgent[MyConfig]):  # ← Wrong!
    ...
```

❌ **DON'T forget required methods**
```python
class MyTaskAgent(BaseLangGraphTaskAgent[MyConfig]):
    # Forgot _process_state_update() ← Will fail!
    pass
```

❌ **DON'T use wrong streaming method**
```python
class MyChatAgent(BaseLangGraphChatAgent[MyConfig]):
    async def _process_state_update(self, ...):  # ← Wrong for chat!
        ...
```

✅ **DO use correct base class**
```python
class MyChatAgent(BaseLangGraphChatAgent[MyConfig]):  # ← Correct!
    async def _build_graph(self): ...
    def _create_initial_state(self, messages): ...
    async def _extract_final_content(self, final_state): ...
```

✅ **DO implement required methods**
```python
class MyTaskAgent(BaseLangGraphTaskAgent[MyConfig]):  # ← Correct!
    async def _build_graph(self): ...
    def _create_initial_state(self, messages): ...
    async def _extract_final_content(self, final_state): ...
    async def _process_state_update(self, ...):  # ← Required!
        ...
```

---

## Support and Resources

### Built-in Examples
- `simple.py` - Simple chat agent implementation
- `workflow.py` - Task/workflow agent implementation
- `test_agent.py` - Plugin test agent with tools

### Documentation
- **This Guide** - Complete development reference
- `base.py` - Comprehensive docstrings in base classes
- `IMPLEMENTATION_SUMMARY.md` - Architecture details

### Getting Help
1. Review this guide and built-in examples
2. Check docstrings in `base.py`
3. Look at test files for usage patterns
4. Review logs for debugging information

---

**Ready to build your agent? Start with the minimal templates above and expand from there!**

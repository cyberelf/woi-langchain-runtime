# LangGraph Agent Templates Guide

This guide explains how to create custom LangGraph agent templates using the provided base classes.

## Table of Contents

1. [Overview](#overview)
2. [Choosing the Right Base Class](#choosing-the-right-base-class)
3. [BaseLangGraphChatAgent](#baselanggraphchatagent)
4. [BaseLangGraphTaskAgent](#baselanggraphtaskagent)
5. [Common Patterns](#common-patterns)
6. [Complete Examples](#complete-examples)
7. [Best Practices](#best-practices)

## Overview

The framework provides three base classes for building LangGraph agents:

1. **BaseLangGraphAgent**: Core functionality (DO NOT inherit directly)
2. **BaseLangGraphChatAgent**: For conversational agents
3. **BaseLangGraphTaskAgent**: For task-oriented agents

The key difference is how they handle streaming:

- **Chat agents** use `"messages"` stream mode → stream every token as it's generated
- **Task agents** use `"updates"` stream mode → stream only significant state changes

## Choosing the Right Base Class

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

## BaseLangGraphChatAgent

### Basic Structure

```python
from pydantic import BaseModel, Field
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphChatAgent
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

# 1. Define your configuration schema
class MyChatAgentConfig(BaseModel):
    """Configuration for my chat agent."""
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_iterations: int = Field(default=5, description="Max reasoning iterations")

# 2. Define your agent class
class MyChatAgent(BaseLangGraphChatAgent[MyChatAgentConfig]):
    """A conversational agent template."""
    
    # Template metadata
    template_name = "My Chat Agent"
    template_id = "my-chat-agent"
    template_version = "1.0.0"
    template_description = "A friendly conversational assistant"
    config_schema = MyChatAgentConfig
    
    # 3. Implement required methods
    async def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph execution graph."""
        # Define your graph here
        workflow = StateGraph(AgentState)
        # ... add nodes, edges, etc.
        return workflow.compile()
    
    def _create_initial_state(self, messages):
        """Convert input messages to graph state."""
        return {
            "messages": self._convert_to_langgraph_messages(messages),
        }
    
    async def _extract_final_content(self, final_state):
        """Extract final response from state."""
        messages = final_state.get("messages", [])
        return messages[-1].content if messages else ""
```

### Customizing Message Chunk Processing

By default, chat agents stream all message chunks. You can customize this:

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
                content=f"[Using {tool_name}]\n",
                finish_reason=None,
                metadata={'chunk_index': chunk_index, 'type': 'tool_indicator'}
            )
        
        # Stream the actual content
        content = str(message.content)
        if content:
            yield StreamingChunk(
                content=content,
                finish_reason=None,
                metadata={'chunk_index': chunk_index}
            )
```

## BaseLangGraphTaskAgent

### Basic Structure

```python
from pydantic import BaseModel, Field
from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphTaskAgent

# 1. Define your configuration schema
class MyTaskAgentConfig(BaseModel):
    """Configuration for my task agent."""
    max_planning_steps: int = Field(default=3, description="Max planning iterations")
    enable_validation: bool = Field(default=True, description="Validate results")

# 2. Define your agent class
class MyTaskAgent(BaseLangGraphTaskAgent[MyTaskAgentConfig]):
    """A task-oriented agent template."""
    
    # Template metadata
    template_name = "My Task Agent"
    template_id = "my-task-agent"
    template_version = "1.0.0"
    template_description = "Executes multi-step workflows"
    config_schema = MyTaskAgentConfig
    
    # 3. Implement required methods
    async def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph execution graph."""
        workflow = StateGraph(WorkflowState)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("validate", self._validate_node)
        # ... add edges and logic
        return workflow.compile()
    
    def _create_initial_state(self, messages):
        """Convert input messages to graph state."""
        return {
            "messages": self._convert_to_langgraph_messages(messages),
            "plan": None,
            "results": [],
            "phase": "planning"
        }
    
    async def _extract_final_content(self, final_state):
        """Extract final response from state."""
        return final_state.get("final_result", "")
    
    # 4. REQUIRED: Implement state update processing
    async def _process_state_update(self, state_update, chunk_index, metadata):
        """Process state updates and stream significant changes."""
        
        # state_update is a dict: {node_name: node_output_state}
        for node_name, node_state in state_update.items():
            
            if node_name == "plan":
                # Stream planning phase
                plan = node_state.get("plan", "")
                if plan:
                    yield StreamingChunk(
                        content=f"📋 Planning: {plan}\n",
                        finish_reason=None,
                        metadata={'phase': 'planning', 'node': node_name}
                    )
            
            elif node_name == "execute":
                # Stream execution results
                result = node_state.get("result", "")
                if result:
                    yield StreamingChunk(
                        content=f"✓ Completed: {result}\n",
                        finish_reason=None,
                        metadata={'phase': 'execution', 'node': node_name}
                    )
            
            elif node_name == "validate":
                # Stream validation outcome
                is_valid = node_state.get("is_valid", False)
                status = "✓ Valid" if is_valid else "⚠ Invalid"
                yield StreamingChunk(
                    content=f"{status}\n",
                    finish_reason=None,
                    metadata={'phase': 'validation', 'node': node_name}
                )
            
            # Internal nodes (like routing) can be skipped by not yielding
```

### Controlling What Gets Streamed

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
                    content=f"{content}\n",
                    finish_reason=None,
                    metadata={'node': node_name}
                )
        
        # Hide internal nodes (don't yield anything)
        elif node_name in ["_internal_routing", "_validation", "_error_check"]:
            # Skip these - users don't need to see them
            pass
        
        # Add progress indicators
        elif node_name == "long_running_task":
            progress = node_state.get("progress", 0)
            yield StreamingChunk(
                content=f"Progress: {progress}%\n",
                finish_reason=None,
                metadata={'node': node_name, 'progress': progress}
            )
```

## Common Patterns

### Pattern 1: ReAct Agent (Chat-based)

```python
class ReActAgent(BaseLangGraphChatAgent[ReActConfig]):
    """ReAct agent with tool calling."""
    
    async def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tool_node)
        
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "end": END}
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    async def _agent_node(self, state):
        messages = state["messages"]
        response = await self.llm_client.ainvoke(messages)
        return {"messages": [response]}
    
    async def _tool_node(self, state):
        messages = state["messages"]
        last_message = messages[-1]
        tool_calls = last_message.tool_calls
        
        tool_outputs = []
        for tool_call in tool_calls:
            result = await self.toolset_client.execute(tool_call)
            tool_outputs.append(result)
        
        return {"messages": tool_outputs}
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
        
        for node_name, node_state in state_update.items():
            phase_emoji = {
                "understand": "🔍",
                "plan": "📋",
                "execute": "⚙️",
                "review": "✓"
            }
            
            emoji = phase_emoji.get(node_name, "•")
            phase_name = node_name.title()
            
            # Stream phase updates
            if node_name == "understand":
                requirements = node_state.get("requirements", [])
                yield StreamingChunk(
                    content=f"{emoji} Understanding: {len(requirements)} requirements identified\n",
                    finish_reason=None,
                    metadata={'phase': node_name}
                )
            
            elif node_name == "plan":
                steps = node_state.get("steps", [])
                yield StreamingChunk(
                    content=f"{emoji} Planning: {len(steps)} steps created\n",
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
                result = node_state.get("result", "")
                yield StreamingChunk(
                    content=f"{emoji} Review complete\n{result}\n",
                    finish_reason=None,
                    metadata={'phase': node_name}
                )
```

### Pattern 3: Hybrid Approach

Sometimes you want task-like control but chat-like streaming:

```python
class HybridAgent(BaseLangGraphTaskAgent[HybridConfig]):
    """Task agent that streams message chunks for certain nodes."""
    
    async def _build_graph(self):
        # Build graph with both task nodes and chat nodes
        workflow = StateGraph(HybridState)
        
        workflow.add_node("analyze", self._analyze_node)  # Task node
        workflow.add_node("chat", self._chat_node)        # Chat node
        # ...
        
        return workflow.compile()
    
    async def _process_state_update(self, state_update, chunk_index, metadata):
        """Mix task updates and chat streaming."""
        
        for node_name, node_state in state_update.items():
            
            if node_name == "analyze":
                # Task-style: stream only the result
                analysis = node_state.get("analysis", "")
                if analysis:
                    yield StreamingChunk(
                        content=f"Analysis: {analysis}\n",
                        finish_reason=None,
                        metadata={'type': 'task', 'node': node_name}
                    )
            
            elif node_name == "chat":
                # Chat-style: stream the full message
                messages = node_state.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    yield StreamingChunk(
                        content=last_msg.content,
                        finish_reason=None,
                        metadata={'type': 'chat', 'node': node_name}
                    )
```

## Complete Examples

### Example 1: Simple Chat Agent

```python
from typing import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END

class SimpleChatConfig(BaseModel):
    temperature: float = Field(default=0.7)

class SimpleChatState(TypedDict):
    messages: list[BaseMessage]

class SimpleChatAgent(BaseLangGraphChatAgent[SimpleChatConfig]):
    template_name = "Simple Chat Agent"
    template_id = "simple-chat"
    template_version = "1.0.0"
    template_description = "A basic conversational agent"
    config_schema = SimpleChatConfig
    
    async def _build_graph(self):
        workflow = StateGraph(SimpleChatState)
        workflow.add_node("chat", self._chat_node)
        workflow.set_entry_point("chat")
        workflow.set_finish_point("chat")
        return workflow.compile()
    
    async def _chat_node(self, state):
        response = await self.llm_client.ainvoke(state["messages"])
        return {"messages": [response]}
    
    def _create_initial_state(self, messages):
        langgraph_messages = self._convert_to_langgraph_messages(messages)
        if self.system_prompt:
            system_msg = SystemMessage(content=self.system_prompt)
            langgraph_messages = [system_msg] + langgraph_messages
        return {"messages": langgraph_messages}
    
    async def _extract_final_content(self, final_state):
        messages = final_state.get("messages", [])
        return messages[-1].content if messages else ""
```

### Example 2: Multi-Step Task Agent

```python
from typing import TypedDict, Literal
from pydantic import BaseModel, Field

class WorkflowConfig(BaseModel):
    max_steps: int = Field(default=10)
    require_validation: bool = Field(default=True)

class WorkflowState(TypedDict):
    messages: list[BaseMessage]
    plan: list[str]
    completed_steps: list[str]
    current_step: int
    final_result: str

class MultiStepAgent(BaseLangGraphTaskAgent[WorkflowConfig]):
    template_name = "Multi-Step Workflow Agent"
    template_id = "multi-step-workflow"
    template_version = "1.0.0"
    template_description = "Executes complex multi-step workflows"
    config_schema = WorkflowConfig
    
    async def _build_graph(self):
        workflow = StateGraph(WorkflowState)
        
        workflow.add_node("create_plan", self._create_plan)
        workflow.add_node("execute_step", self._execute_step)
        workflow.add_node("validate_step", self._validate_step)
        workflow.add_node("finalize", self._finalize)
        
        workflow.set_entry_point("create_plan")
        workflow.add_edge("create_plan", "execute_step")
        
        workflow.add_conditional_edges(
            "execute_step",
            self._should_validate,
            {"validate": "validate_step", "continue": "execute_step", "done": "finalize"}
        )
        
        workflow.add_edge("validate_step", "execute_step")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _create_initial_state(self, messages):
        return {
            "messages": self._convert_to_langgraph_messages(messages),
            "plan": [],
            "completed_steps": [],
            "current_step": 0,
            "final_result": ""
        }
    
    async def _extract_final_content(self, final_state):
        return final_state.get("final_result", "")
    
    async def _process_state_update(self, state_update, chunk_index, metadata):
        """Stream workflow progress."""
        
        for node_name, node_state in state_update.items():
            
            if node_name == "create_plan":
                plan = node_state.get("plan", [])
                yield StreamingChunk(
                    content=f"📋 Created plan with {len(plan)} steps\n",
                    finish_reason=None,
                    metadata={'phase': 'planning'}
                )
            
            elif node_name == "execute_step":
                current = node_state.get("current_step", 0)
                total = len(node_state.get("plan", []))
                step_desc = node_state.get("plan", [])[current] if current < total else ""
                
                yield StreamingChunk(
                    content=f"⚙️ Step {current + 1}/{total}: {step_desc}\n",
                    finish_reason=None,
                    metadata={'phase': 'execution', 'step': current}
                )
            
            elif node_name == "validate_step":
                is_valid = node_state.get("validation_passed", False)
                status = "✓" if is_valid else "⚠"
                yield StreamingChunk(
                    content=f"{status} Validation {'passed' if is_valid else 'failed'}\n",
                    finish_reason=None,
                    metadata={'phase': 'validation'}
                )
            
            elif node_name == "finalize":
                result = node_state.get("final_result", "")
                yield StreamingChunk(
                    content=f"✓ Workflow complete\n",
                    finish_reason=None,
                    metadata={'phase': 'finalization'}
                )
    
    # Node implementations
    async def _create_plan(self, state):
        # Create execution plan
        messages = state["messages"]
        plan_prompt = "Create a step-by-step plan to accomplish this task."
        # ... use LLM to create plan
        return {"plan": ["step1", "step2", "step3"]}
    
    async def _execute_step(self, state):
        # Execute current step
        current = state["current_step"]
        plan = state["plan"]
        # ... execute the step
        return {
            "completed_steps": state["completed_steps"] + [plan[current]],
            "current_step": current + 1
        }
    
    async def _validate_step(self, state):
        # Validate the completed step
        # ... validation logic
        return {"validation_passed": True}
    
    async def _finalize(self, state):
        # Create final result
        completed = state["completed_steps"]
        result = f"Completed {len(completed)} steps successfully"
        return {"final_result": result}
    
    def _should_validate(self, state) -> Literal["validate", "continue", "done"]:
        current = state["current_step"]
        plan = state["plan"]
        
        if current >= len(plan):
            return "done"
        
        if self.config.require_validation:
            return "validate"
        
        return "continue"
```

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
        description="Maximum number of reasoning iterations before stopping"
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
```

### 2. Error Handling

```python
async def _build_graph(self):
    try:
        workflow = StateGraph(MyState)
        # ... build graph
        return workflow.compile()
    except Exception as e:
        logger.error(f"Failed to build graph: {e}")
        raise
```

### 3. Logging

```python
async def _process_state_update(self, state_update, chunk_index, metadata):
    logger.debug(f"Processing update #{chunk_index}: {list(state_update.keys())}")
    
    for node_name, node_state in state_update.items():
        logger.debug(f"Node {node_name} output: {node_state}")
        # ... process
```

### 4. Testing Your Template

```python
import pytest
from runtime.domain.value_objects.agent_configuration import AgentConfiguration

@pytest.mark.asyncio
async def test_my_agent():
    config = AgentConfiguration(
        system_prompt="You are a helpful assistant",
        llm_config_id="gpt-4",
        template_configuration={
            "temperature": 0.7,
            "max_iterations": 5
        }
    )
    
    agent = MyAgent(config, llm_service, toolset_service)
    
    messages = [ChatMessage(role="user", content="Hello")]
    result = await agent.execute(messages)
    
    assert result.success
    assert result.message
```

### 5. Documentation

Always document:
- What your agent does
- When to use it
- Configuration options
- Example usage
- Limitations

```python
class MyAgent(BaseLangGraphChatAgent[MyConfig]):
    """
    My Agent - A specialized assistant for X.
    
    This agent is designed for:
    - Task A
    - Task B
    - Task C
    
    It uses a Y approach with Z capabilities.
    
    Example:
        ```python
        config = MyConfig(temperature=0.7)
        agent = MyAgent(config, llm_service)
        result = await agent.execute(messages)
        ```
    
    Limitations:
    - Cannot handle very long documents (>10k tokens)
    - Requires internet access for API calls
    """
```

## Summary

- **Chat Agents** (`BaseLangGraphChatAgent`): Stream every token, best for conversations
- **Task Agents** (`BaseLangGraphTaskAgent`): Stream only state changes, best for workflows
- Override `_process_message_chunk()` for chat agents to customize streaming
- Override `_process_state_update()` for task agents to control what's streamed
- Always implement: `_build_graph()`, `_create_initial_state()`, `_extract_final_content()`
- Use proper configuration schemas with Pydantic
- Add logging, error handling, and documentation

For more examples, see the templates in the `templates/` directory.

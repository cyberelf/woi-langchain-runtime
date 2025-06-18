"""Agent management and execution logic using LangChain/LangGraph."""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from .config import settings
from .llm_client import llm_client
from .models import (
    AgentType, AgentCreateRequest, ChatMessage, MessageRole,
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk,
    ChatChoice, ChatUsage, ExecutionStep, ChatCompletionMetadata,
    FinishReason
)


class AgentState(BaseModel):
    """State for LangGraph agent execution."""
    messages: List[BaseMessage] = []
    agent_id: str = ""
    agent_type: AgentType = AgentType.CONVERSATION
    system_prompt: str = ""
    llm_config_id: str = ""
    template_config: Dict[str, Any] = {}
    conversation_config: Dict[str, Any] = {}
    execution_steps: List[ExecutionStep] = []
    tools_used: List[str] = []
    start_time: float = 0.0
    metadata: Dict[str, Any] = {}


class BaseAgent:
    """Base agent class."""
    
    def __init__(self, agent_data: AgentCreateRequest) -> None:
        self.id = agent_data.id
        self.name = agent_data.name
        self.description = agent_data.description
        self.type = agent_data.type
        self.template_id = agent_data.template_id
        self.template_version_id = agent_data.template_version_id
        self.template_config = agent_data.template_config
        self.system_prompt = agent_data.system_prompt
        self.conversation_config = agent_data.conversation_config or {}
        self.toolsets = agent_data.toolsets  # Selected toolsets
        self.llm_config_id = agent_data.llm_config_id
        
        # Execution metrics
        self.total_executions = 0
        self.total_response_time = 0.0
        self.error_count = 0
        
        # Build the agent graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph execution graph."""
        # Create a simple graph with message handling
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("process_message", self._process_message)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("process_message")
        workflow.add_edge("process_message", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def _process_message(self, state: AgentState) -> AgentState:
        """Process incoming message."""
        step_start = time.time()
        
        # Add system message if not present
        if not any(isinstance(msg, SystemMessage) for msg in state.messages):
            system_msg = SystemMessage(content=self.system_prompt)
            state.messages.insert(0, system_msg)
        
        # Apply conversation history limits
        history_limit = self.conversation_config.get("historyLength", 10)
        if len(state.messages) > history_limit + 1:  # +1 for system message
            # Keep system message and recent messages
            system_msgs = [msg for msg in state.messages if isinstance(msg, SystemMessage)]
            other_msgs = [msg for msg in state.messages if not isinstance(msg, SystemMessage)]
            state.messages = system_msgs + other_msgs[-history_limit:]
        
        step_duration = int((time.time() - step_start) * 1000)
        state.execution_steps.append(ExecutionStep(
            step="process_message",
            status="completed",
            duration_ms=step_duration
        ))
        
        return state
    
    async def _generate_response(self, state: AgentState) -> AgentState:
        """Generate response using LLM."""
        step_start = time.time()
        
        try:
            # Convert LangChain messages to ChatMessage format
            chat_messages = []
            for msg in state.messages:
                if isinstance(msg, HumanMessage):
                    chat_messages.append(ChatMessage(role=MessageRole.USER, content=msg.content))
                elif isinstance(msg, AIMessage):
                    chat_messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=msg.content))
                elif isinstance(msg, SystemMessage):
                    chat_messages.append(ChatMessage(role=MessageRole.SYSTEM, content=msg.content))
            
            # Call LLM
            response = await llm_client.chat_completion(
                messages=chat_messages,
                llm_config_id=state.llm_config_id,
                stream=False
            )
            
            # Extract response content
            if response.get("choices") and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                state.messages.append(AIMessage(content=content))
            
            step_duration = int((time.time() - step_start) * 1000)
            state.execution_steps.append(ExecutionStep(
                step="generate_response",
                status="completed",
                duration_ms=step_duration
            ))
            
        except Exception as e:
            step_duration = int((time.time() - step_start) * 1000)
            state.execution_steps.append(ExecutionStep(
                step="generate_response",
                status="error",
                duration_ms=step_duration
            ))
            raise RuntimeError(f"Response generation failed: {e}")
        
        return state
    
    async def execute(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatCompletionResponse:
        """Execute the agent with given messages."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        try:
            # Convert ChatMessage to LangChain messages
            langchain_messages = []
            for msg in messages:
                if msg.role == MessageRole.USER:
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.role == MessageRole.ASSISTANT:
                    langchain_messages.append(AIMessage(content=msg.content))
                elif msg.role == MessageRole.SYSTEM:
                    langchain_messages.append(SystemMessage(content=msg.content))
            
            # Create initial state
            initial_state = AgentState(
                messages=langchain_messages,
                agent_id=self.id,
                agent_type=self.type,
                system_prompt=self.system_prompt,
                llm_config_id=self.llm_config_id,
                template_config=self.template_config,
                conversation_config=self.conversation_config.dict() if hasattr(self.conversation_config, 'dict') else self.conversation_config,
                execution_steps=[],
                tools_used=[],
                start_time=start_time,
                metadata=metadata or {}
            )
            
            # Execute the graph
            final_state = await self.graph.ainvoke(initial_state)
            
            # Extract the final response
            assistant_messages = [
                msg for msg in final_state.messages 
                if isinstance(msg, AIMessage)
            ]
            
            if not assistant_messages:
                raise RuntimeError("No response generated")
            
            final_message = assistant_messages[-1]
            processing_time = int((time.time() - start_time) * 1000)
            
            # Update metrics
            self.total_executions += 1
            self.total_response_time += processing_time
            
            # Create response
            response = ChatCompletionResponse(
                id=completion_id,
                created=int(time.time()),
                model=self.id,
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(
                            role=MessageRole.ASSISTANT,
                            content=final_message.content
                        ),
                        finish_reason=FinishReason.STOP
                    )
                ],
                usage=ChatUsage(
                    prompt_tokens=0,  # Would need to calculate
                    completion_tokens=0,  # Would need to calculate
                    total_tokens=0
                ),
                metadata=ChatCompletionMetadata(
                    agent_id=self.id,
                    agent_type=self.type,
                    processing_time_ms=processing_time,
                    execution_steps=final_state.execution_steps,
                    tools_used=final_state.tools_used,
                    confidence_score=0.9  # Placeholder
                )
            )
            
            return response
            
        except Exception as e:
            self.error_count += 1
            raise RuntimeError(f"Agent execution failed: {e}")
    
    async def stream_execute(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Execute the agent with streaming response."""
        start_time = time.time()
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        try:
            # For simplicity, we'll execute normally and simulate streaming
            response = await self.execute(
                messages=messages,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata=metadata
            )
            
            # Simulate streaming by chunking the response
            content = response.choices[0].message.content
            words = content.split()
            
            for i, word in enumerate(words):
                chunk_content = word + (" " if i < len(words) - 1 else "")
                
                chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=int(time.time()),
                    model=self.id,
                    choices=[{
                        "index": 0,
                        "delta": {"content": chunk_content},
                        "finish_reason": None
                    }]
                )
                
                yield chunk
                await asyncio.sleep(0.05)  # Small delay for streaming effect
            
            # Final chunk with finish reason
            final_chunk = ChatCompletionChunk(
                id=completion_id,
                created=int(time.time()),
                model=self.id,
                choices=[{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }],
                usage=response.usage
            )
            
            yield final_chunk
            
        except Exception as e:
            self.error_count += 1
            raise RuntimeError(f"Agent streaming execution failed: {e}")


class TaskAgent(BaseAgent):
    """Task-oriented agent with step-by-step execution."""
    
    def _build_graph(self) -> StateGraph:
        """Build task-specific execution graph."""
        workflow = StateGraph(AgentState)
        
        # Add nodes for task execution
        workflow.add_node("validate_task", self._validate_task)
        workflow.add_node("execute_steps", self._execute_steps)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("validate_task")
        workflow.add_edge("validate_task", "execute_steps")
        workflow.add_edge("execute_steps", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def _validate_task(self, state: AgentState) -> AgentState:
        """Validate task configuration."""
        step_start = time.time()
        
        task_config = state.template_config.get("taskSteps", {})
        steps = task_config.get("steps", [])
        
        if not steps:
            raise ValueError("No task steps defined")
        
        step_duration = int((time.time() - step_start) * 1000)
        state.execution_steps.append(ExecutionStep(
            step="validate_task",
            status="completed",
            duration_ms=step_duration
        ))
        
        return state
    
    async def _execute_steps(self, state: AgentState) -> AgentState:
        """Execute task steps."""
        step_start = time.time()
        
        task_config = state.template_config.get("taskSteps", {})
        steps = task_config.get("steps", [])
        step_timeout = task_config.get("stepTimeout", 300)
        retry_count = task_config.get("retryCount", 2)
        
        # Execute each step (simplified implementation)
        for i, step_name in enumerate(steps):
            step_execution_start = time.time()
            
            try:
                # Simulate step execution
                await asyncio.sleep(0.1)  # Placeholder for actual step logic
                
                step_duration = int((time.time() - step_execution_start) * 1000)
                state.execution_steps.append(ExecutionStep(
                    step=f"task_step_{i+1}_{step_name}",
                    status="completed",
                    duration_ms=step_duration
                ))
                
            except Exception as e:
                step_duration = int((time.time() - step_execution_start) * 1000)
                state.execution_steps.append(ExecutionStep(
                    step=f"task_step_{i+1}_{step_name}",
                    status="error",
                    duration_ms=step_duration
                ))
                
                if retry_count > 0:
                    # Implement retry logic here
                    pass
                else:
                    raise RuntimeError(f"Task step failed: {step_name}")
        
        total_duration = int((time.time() - step_start) * 1000)
        state.execution_steps.append(ExecutionStep(
            step="execute_steps",
            status="completed",
            duration_ms=total_duration
        ))
        
        return state


class CustomAgent(BaseAgent):
    """Custom agent with user-defined code execution."""
    
    def _build_graph(self) -> StateGraph:
        """Build custom execution graph."""
        workflow = StateGraph(AgentState)
        
        # Add nodes for custom execution
        workflow.add_node("validate_code", self._validate_code)
        workflow.add_node("execute_code", self._execute_code)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("validate_code")
        workflow.add_edge("validate_code", "execute_code")
        workflow.add_edge("execute_code", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def _validate_code(self, state: AgentState) -> AgentState:
        """Validate custom code configuration."""
        step_start = time.time()
        
        code_config = state.template_config.get("codeSource", {})
        runtime_config = state.template_config.get("runtime", {})
        
        if not code_config.get("content"):
            raise ValueError("No code content provided")
        
        if not runtime_config.get("language"):
            raise ValueError("No runtime language specified")
        
        step_duration = int((time.time() - step_start) * 1000)
        state.execution_steps.append(ExecutionStep(
            step="validate_code",
            status="completed",
            duration_ms=step_duration
        ))
        
        return state
    
    async def _execute_code(self, state: AgentState) -> AgentState:
        """Execute custom code (placeholder implementation)."""
        step_start = time.time()
        
        # This is a placeholder - in a real implementation, you would:
        # 1. Set up a secure execution environment
        # 2. Install dependencies
        # 3. Execute the code with proper sandboxing
        # 4. Capture output and errors
        
        code_config = state.template_config.get("codeSource", {})
        runtime_config = state.template_config.get("runtime", {})
        
        language = runtime_config.get("language")
        timeout = runtime_config.get("timeout", 30)
        memory_limit = runtime_config.get("memoryLimit", 512)
        
        # Simulate code execution
        await asyncio.sleep(0.2)
        
        step_duration = int((time.time() - step_start) * 1000)
        state.execution_steps.append(ExecutionStep(
            step="execute_code",
            status="completed",
            duration_ms=step_duration
        ))
        
        return state


class AgentManager:
    """Manager for agent instances."""
    
    def __init__(self) -> None:
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_metrics = {
            "active_agents": 0,
            "total_executions": 0,
            "total_response_time": 0.0,
            "error_count": 0
        }
    
    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgent:
        """Create a new agent instance."""
        if agent_data.id in self.agents:
            raise ValueError(f"Agent with ID {agent_data.id} already exists")
        
        # Create appropriate agent type
        if agent_data.type == AgentType.TASK:
            agent = TaskAgent(agent_data)
        elif agent_data.type == AgentType.CUSTOM:
            agent = CustomAgent(agent_data)
        else:
            agent = BaseAgent(agent_data)
        
        self.agents[agent_data.id] = agent
        self.agent_metrics["active_agents"] = len(self.agents)
        
        return agent
    
    def update_agent(self, agent_id: str, agent_data: AgentCreateRequest) -> BaseAgent:
        """Update an existing agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent with ID {agent_id} not found")
        
        # For simplicity, we'll recreate the agent
        # In a production system, you might want to update in place
        old_agent = self.agents[agent_id]
        
        # Preserve metrics
        if agent_data.type == AgentType.TASK:
            new_agent = TaskAgent(agent_data)
        elif agent_data.type == AgentType.CUSTOM:
            new_agent = CustomAgent(agent_data)
        else:
            new_agent = BaseAgent(agent_data)
        
        # Transfer metrics
        new_agent.total_executions = old_agent.total_executions
        new_agent.total_response_time = old_agent.total_response_time
        new_agent.error_count = old_agent.error_count
        
        self.agents[agent_id] = new_agent
        return new_agent
    
    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent with ID {agent_id} not found")
        
        del self.agents[agent_id]
        self.agent_metrics["active_agents"] = len(self.agents)
    
    def get_agent(self, agent_id: str) -> BaseAgent:
        """Get an agent by ID."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent with ID {agent_id} not found")
        
        return self.agents[agent_id]
    
    def update_metrics(self) -> None:
        """Update global metrics from all agents."""
        total_executions = 0
        total_response_time = 0.0
        error_count = 0
        
        for agent in self.agents.values():
            total_executions += agent.total_executions
            total_response_time += agent.total_response_time
            error_count += agent.error_count
        
        self.agent_metrics.update({
            "active_agents": len(self.agents),
            "total_executions": total_executions,
            "average_response_time_ms": int(total_response_time / max(total_executions, 1)),
            "error_rate": error_count / max(total_executions, 1)
        })
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        self.update_metrics()
        return self.agent_metrics.copy()


# Global agent manager
agent_manager = AgentManager() 
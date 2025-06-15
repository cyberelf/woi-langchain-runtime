"""Conversation Agent Template - Customer Service Bot."""

import time
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from .base import BaseAgentTemplate, ValidationResult
from ..models import (
    AgentType, ChatMessage, MessageRole, ChatCompletionResponse, 
    ChatCompletionChunk, ChatChoice, ChatUsage, ExecutionStep, 
    ChatCompletionMetadata, FinishReason
)
from ..llm_client import llm_client


class ConversationAgent(BaseAgentTemplate):
    """
    Conversation Agent Template for customer service scenarios.
    
    This agent provides basic conversational AI capabilities with
    configurable conversation history and continuous mode.
    """
    
    # Template Metadata (class variables)
    template_name: str = "智能客服助手"
    template_id: str = "customer-service-bot"
    template_version: str = "1.0.0"
    template_description: str = "基础对话型智能体，适用于客服、咨询等场景，支持连续对话和历史记录管理"
    agent_type: AgentType = AgentType.CONVERSATION
    
    # Configuration Schema
    config_schema: Dict[str, Any] = {
        "continuous": {
            "type": "boolean",
            "default": True,
            "description": "是否启用连续对话模式，保持上下文连贯性",
            "order": 0
        },
        "historyLength": {
            "type": "integer",
            "default": 10,
            "minimum": 5,
            "maximum": 100,
            "description": "对话历史长度，影响AI记忆的对话轮数",
            "order": 1
        },
        "temperature": {
            "type": "number",
            "default": 0.7,
            "minimum": 0.0,
            "maximum": 2.0,
            "description": "回复创造性程度，0为最保守，2为最有创造性",
            "order": 2
        },
        "systemPrompt": {
            "type": "string",
            "default": "你是一个专业、友好的客服助手。请以礼貌、耐心的态度帮助用户解决问题。",
            "description": "系统提示词，定义AI的角色和行为风格",
            "order": 3
        }
    }
    
    # Runtime Requirements
    runtime_requirements: Dict[str, Any] = {
        "memory": "256MB",
        "cpu": "0.1 cores",
        "gpu": False,
        "estimatedLatency": "< 2s"
    }
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> ValidationResult:
        """Enhanced validation for conversation agent configuration."""
        # First do basic validation
        result = super().validate_config(config)
        
        # Add specific validations
        if "systemPrompt" in config:
            system_prompt = config["systemPrompt"]
            if len(system_prompt) > 4000:
                result.errors.append("System prompt must be less than 4000 characters")
            if len(system_prompt.strip()) == 0:
                result.warnings.append("Empty system prompt may lead to inconsistent behavior")
        
        # Check temperature range more strictly
        if "temperature" in config:
            temp = config["temperature"]
            if temp < 0.1:
                result.warnings.append("Very low temperature may make responses too rigid")
            elif temp > 1.5:
                result.warnings.append("High temperature may make responses unpredictable")
        
        result.valid = len(result.errors) == 0
        return result
    
    def _build_graph(self) -> StateGraph:
        """Build the conversation agent graph."""
        from ..agents import AgentState  # Import here to avoid circular imports
        
        workflow = StateGraph(AgentState)
        
        # Add nodes for conversation flow
        workflow.add_node("process_message", self._process_message)
        workflow.add_node("generate_response", self._generate_response)
        
        # Set up the flow
        workflow.set_entry_point("process_message")
        workflow.add_edge("process_message", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def _process_message(self, state) -> Any:
        """Process incoming message for conversation."""
        step_start = time.time()
        
        # Add system message if not present
        system_prompt = self.template_config.get("systemPrompt", self.system_prompt)
        if not any(isinstance(msg, SystemMessage) for msg in state.messages):
            system_msg = SystemMessage(content=system_prompt)
            state.messages.insert(0, system_msg)
        
        # Apply conversation history limits
        history_limit = self.template_config.get("historyLength", 10)
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
    
    async def _generate_response(self, state) -> Any:
        """Generate conversational response."""
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
            
            # Use temperature from config
            temperature = self.template_config.get("temperature", 0.7)
            
            # Call LLM
            response = await llm_client.chat_completion(
                messages=chat_messages,
                llm_config_id=state.llm_config_id,
                stream=False,
                temperature=temperature
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
        """Execute the conversation agent."""
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
            from ..agents import AgentState  # Import here to avoid circular imports
            initial_state = AgentState(
                messages=langchain_messages,
                agent_id=self.id,
                agent_type=self.agent_type,
                system_prompt=self.system_prompt,
                llm_config_id=self.llm_config_id,
                template_config=self.template_config,
                conversation_config=self.conversation_config,
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
                    agent_type=self.agent_type,
                    processing_time_ms=processing_time,
                    execution_steps=final_state.execution_steps,
                    tools_used=final_state.tools_used,
                    confidence_score=None
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
        """Stream execution for real-time responses."""
        # Implementation for streaming would go here
        # For now, just yield a simple chunk
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        chunk = ChatCompletionChunk(
            id=completion_id,
            created=int(time.time()),
            model=self.id,
            choices=[{
                "index": 0,
                "delta": {"content": "Streaming not yet implemented"},
                "finish_reason": None
            }]
        )
        
        yield chunk 
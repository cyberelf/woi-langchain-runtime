"""Workflow Agent Template - Executes a series of steps sequentially.

This template allows agents to execute predefined workflows with multiple steps,
progress tracking, and error handling. 

Each step is a natural language prompt together with configuration that will be executed by the LLM.
```
{
    "name": "Step 1",
    "prompt": "Step 1 prompt",
    "depends_on": [],
    "timeout": 60,
    "retry_count": 0
}
```
"""

import logging
from collections.abc import AsyncGenerator
from math import e, log
from socket import AI_ADDRCONFIG
from typing import Annotated, Any, Literal, Optional, Self, final, override
from enum import Enum
import uuid

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages, RemoveMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately  

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Select, over

from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
from runtime.infrastructure.frameworks.langgraph.toolsets.service import LangGraphToolsetService
from runtime.core.executors import StreamingChunk
from runtime.domain.value_objects.chat_message import ChatMessage
from runtime.domain.value_objects.agent_configuration import AgentConfiguration
from .base import BaseLangGraphTaskAgent

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

class StepResult(str, Enum):
    """Result of a workflow step."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class WorkflowStepConfig(BaseModel):
    """Configuration for a single workflow step (immutable)."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4().hex[:8]), 
        description="Unique identifier for the step"
    )
    name: str = Field(..., description="Human-readable name for the step")
    prompt: str = Field(..., description="Prompt/instruction for this step")
    tools: list[str] = Field(default_factory=list, description="Tools can be used for this step")
    depends_on: Optional[list[str]] = Field(default=None, description="Step dependencies (defaults to previous step if not specified), empty list means no dependencies")
    timeout: int = Field(default=60, ge=5, le=300, description="Timeout in seconds")
    retry_count: int = Field(default=0, ge=0, le=3, description="Number of retries on failure")


class WorkflowStepState(BaseModel):
    """Runtime execution state for a workflow step."""
    
    step_id: str = Field(..., description="ID of the step this state belongs to")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current status")
    result: Optional[StepResult] = Field(default=None, description="Result status of the step execution")
    result_content: Optional[str] = Field(default=None, description="Actual content result of the step")
    error: Optional[str] = Field(default=None, description="Error message if step failed")
    attempts: int = Field(default=0, description="Number of execution attempts")


class WorkflowState(BaseModel):
    """State of the entire workflow."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    input: str = Field(..., description="Input for the workflow")
    step_configs: list[WorkflowStepConfig] = Field(..., description="Workflow step configurations (immutable)")
    step_states: dict[str, WorkflowStepState] = Field(default_factory=dict, description="Runtime state for each step (keyed by step_id)")
    current_step: int = Field(default=0, description="Index of current step")
    completed_steps: int = Field(default=0, description="Number of completed steps")
    failed_steps: int = Field(default=0, description="Number of failed steps")
    status: str = Field(default="running", description="Overall workflow status")
    context: dict[str, Any] = Field(default_factory=dict, description="Shared context between steps")   # TODO: not used for now
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list, description="Conversation messages")
    should_use_workflow: bool = Field(default=True, description="Whether to execute workflow steps or respond directly")
    response: Optional[str] = Field(default=None, description="Final response - either from routing (direct response) or from last completed step")


class WorkflowAgentConfig(BaseModel):
    """Configuration for Workflow Agent."""
    
    steps: list[WorkflowStepConfig] = Field(
        ..., 
        description="name and description of each step"
    )
    workflow_responsibility: Optional[str] = Field(
        default=None,
        description="Description of what this workflow is responsible for. If provided, a routing node will check if the request is relevant before executing workflow steps."
    )
    history_size: int = Field(
        default=10,
        ge=0,
        description="Number of previous messages to retain in context"
    )
    max_retries: int = Field(
        default=2, 
        ge=0, 
        le=5, 
        description="Maximum retries per step"
    )
    step_timeout: int = Field(
        default=60, 
        ge=5, 
        le=300, 
        description="Default timeout per step in seconds"
    )
    fail_on_error: bool = Field(
        default=True, 
        description="Whether to stop workflow on step failure"
    )

    @field_validator('steps')
    def validate_step_configs(cls, v: list[WorkflowStepConfig]) -> list[WorkflowStepConfig]:
        """Validate step configs to ensure unique IDs and valid dependencies."""
        if len(v) == 0:
            raise ValueError("Workflow must have at least one step")
        
        step_ids = {step.id for step in v}
        if len(step_ids) != len(v):
            raise ValueError("Step IDs must be unique")
        
        for step in v:
            if step.depends_on:
                for dep in step.depends_on:
                    if dep not in step_ids:
                        raise ValueError(f"Step '{step.name}' has invalid dependency '{dep}'")
        
        return v
    

SYSTEM_PROMPT_TEMPLATE = """
You are a workflow execution agent. You should complete the task step according to the workflow status.

## Setpup Instructions:
{system_prompt}

## Workflow Steps
You are strictly following the steps:
{workflow_steps}

## Step Control Commands
Control the current step execution by including one of these commands at the end of your response:

- WORKING - Continue to working on the current step  (default behavior)
- SUCCESS - Mark this step as success and proceed to the next step
- FAIL - Mark this step as failed

The command controls only the current step but NOT the entire workflow.
The command should be on a separate line in your response.

"""

USER_PROMPT_TEMPLATE = """
Here is the overall workflow status:

<workflow_status>
{workflow_status}
</workflow_status>

Now you are executing the step 
<step>
{step_name}: {step_prompt}
</step>

And you need to finish the step according to the user input.

<input>
{input}
</input>

"""

class WorkflowAgent(BaseLangGraphTaskAgent[WorkflowAgentConfig]):

    @staticmethod
    def strip_workflow_control_commands(text: str) -> str:
        """Remove workflow control commands (SUCCESS, FAIL, WORKING) from text."""
        if not text:
            return ""
        lines = text.splitlines()
        filtered = [line for line in lines if line.strip() not in ("SUCCESS", "FAIL", "WORKING")]
        return "\n".join(filtered).strip()
    """Workflow agent template that executes steps sequentially."""
    
    # Template metadata (class variables)
    template_name: str = "Workflow Agent"
    template_id: str = "langgraph-workflow"
    template_version: str = "1.0.0"
    template_description: str = "Executes predefined workflows with multiple steps and progress tracking"
    framework: str = "langgraph"
    
    # Configuration schema (class variables)
    config_schema: type[WorkflowAgentConfig] = WorkflowAgentConfig
    
    def __init__(
        self,
        configuration: AgentConfiguration,
        llm_service: LangGraphLLMService,
        toolset_service: Optional[LangGraphToolsetService] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize the workflow agent."""
        super().__init__(configuration, llm_service, toolset_service, metadata)
        self._graph: CompiledStateGraph | None = None
        
        # Set default depends_on for steps if not specified
        for i, step in enumerate(self.config.steps):
            if step.depends_on is None:
                if i == 0:
                    step.depends_on = []
                else:
                    step.depends_on = [self.config.steps[i-1].id]
        
        # Store workflow step configurations (immutable)
        self.workflow_step_configs = self.config.steps

        # Extract other configuration from typed config object
        self.max_retries = self.config.max_retries
        self.step_timeout = self.config.step_timeout
        self.fail_on_error = self.config.fail_on_error
        self.history_size = self.config.history_size

    def _get_or_create_step_state(self, state: WorkflowState, step_id: str) -> WorkflowStepState:
        """Get or create a step state for the given step ID."""
        if step_id not in state.step_states:
            state.step_states[step_id] = WorkflowStepState(step_id=step_id)
        return state.step_states[step_id]

    def _get_prompts(self, state: WorkflowState) -> tuple[str, str]:
        """Get the system prompt for the step."""
        step_config = state.step_configs[state.current_step]

        workflow_status = ""
        steps = ""
        for step_cfg in self.workflow_step_configs[:state.current_step + 1]:
            workflow_status += f"{step_cfg.name} "
            steps += f"- {step_cfg.name}: {step_cfg.prompt}\n"
            
            # Get step state to check status
            step_state = state.step_states.get(step_cfg.id)
            if step_state:
                if step_state.status == StepStatus.COMPLETED:
                    if step_state.result == StepResult.SUCCESS:
                        workflow_status += " [Success]"
                    elif step_state.result == StepResult.FAILED:
                        workflow_status += " [Failed]"
                    elif step_state.result == StepResult.SKIPPED:
                        workflow_status += " [Skipped]"
                    elif step_state.result == StepResult.ERROR:
                        workflow_status += " [Error]"
                elif step_state.status == StepStatus.RUNNING:
                    workflow_status += " [Running]"
                workflow_status += "\n"
        
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            system_prompt=self.system_prompt,
            workflow_steps=steps
        )
        user_prompt = USER_PROMPT_TEMPLATE.format(
            workflow_status=workflow_status.strip(),
            input=state.input,
            step_name=step_config.name,
            step_prompt=step_config.prompt
        )

        return system_prompt, user_prompt

    async def get_tools(self, tool_name_list: list[str]) -> list[BaseTool]:
        """Get the tools for the workflow."""
        if self.toolset_client is None:
            return []
        all_tools = await self.toolset_client.tools
        return [tool for tool in all_tools if tool.name in tool_name_list]


    def _parse_message(self, message: BaseMessage) -> dict[str, Any]:
        """Parse content and workflow control commands from LLM response.
        
        Supported commands:
        - SUCCESS - Complete the step successfully (default)
        - WORKING - Continue to working on the current step
        - FAIL - Fail the workflow
        """
        response = message.content if isinstance(message.content, str) else str(message.content)

        result = {"step_control": "SUCCESS", "content": ""}  # Default to SUCCESS for step completion
        
        if not response:
            return result
        
        lines = response.split('\n')
        content = ""   # content without command
        for line in lines:
            stripped_line = line.strip()

            if stripped_line == 'SUCCESS':
                result["step_control"] = "SUCCESS"
                break  # SUCCESS takes precedence
                
            elif stripped_line == 'FAIL':
                result["step_control"] = "FAIL"
                break  # FAIL takes precedence
                
            elif stripped_line == 'WORKING':
                result["step_control"] = "WORKING"
            else:
                content += line + "\n"

        result["content"] = content
        return result

    def _process_step_completion(
        self, state: WorkflowState, result: BaseMessage
    ) -> WorkflowState:
        """Process step completion with workflow command parsing."""
        # Parse LLM response message
        response = self._parse_message(result)
        message = result.model_copy()
        message.content = response["content"]
        state.messages.append(message)

        # Parse LLM result for workflow state changes
        step_config = state.step_configs[state.current_step]
        step_state = self._get_or_create_step_state(state, step_config.id)
        
        # Apply workflow state changes (this will set status and result)
        step_control = response.get("step_control", "SUCCESS")  # Default to SUCCESS
        if step_control == "SUCCESS":
            # Mark current step as completed and finish workflow
            step_state.status = StepStatus.COMPLETED
            step_state.result = StepResult.SUCCESS
            step_state.result_content = response["content"]
            state.response = response["content"]  # Store as final response
            
            if state.current_step >= len(state.step_configs) - 1:
                # This was the last step
                state.status = "completed"
                state.completed_steps += 1
            else:
                # Move to next step
                state.completed_steps += 1
                state.current_step += 1
            
        elif step_control == "FAIL":
            # Mark current step as failed and fail workflow
            step_state.status = StepStatus.COMPLETED
            step_state.result = StepResult.FAILED
            step_state.result_content = response["content"]
            state.response = response["content"]  # Store as final response even on failure
            state.status = "failed"
            state.completed_steps += 1
            state.failed_steps += 1
            
        else:  # WORKING (default)
            # Continue working on the current step
            step_state.status = StepStatus.RUNNING
            step_state.result_content = response["content"]

        return state

    
    async def _execute_step_node(self, state: WorkflowState) -> WorkflowState:
        """Execute the current workflow step (individual LangGraph node)."""
        if state.current_step >= len(state.step_configs):
            logger.debug(f"🏁 Workflow completed: step {state.current_step} >= {len(state.step_configs)}")
            return state
            
        step_config = state.step_configs[state.current_step]
        step_state = self._get_or_create_step_state(state, step_config.id)
        
        logger.info(f"⚡ Executing workflow step {state.current_step + 1}/{len(state.step_configs)}: {step_config.name}")
        logger.debug(f"🔍 Step details - tools: {len(step_config.tools)}, "
                    f"depends_on: {step_config.depends_on}")
        
        step_state.status = StepStatus.RUNNING
          
        # Execute the step using base class utility
        system_prompt, user_prompt = self._get_prompts(state)
        tools = await self.get_tools(step_config.tools)
        logger.debug(f"✅ Tools loaded: {[tool.name for tool in tools]}")

        # Compose the prompt messages
        prompt_messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt)
        ]
        # Optionally, prepend prior conversation history if needed
        history_message = trim_messages(state.messages[-self.history_size:], strategy="last", max_tokens=1000, token_counter=count_tokens_approximately, start_on="human")

        logger.debug(f"💬 Including {len(history_message)} previous messages in context")
        prompt_messages = prompt_messages + history_message + [HumanMessage(content=user_prompt)]

        logger.debug(f"🤖 Invoking LLM for step '{step_config.name}' with {len(prompt_messages)} messages")
        
        # Execute LLM with tools if available and supported
        if tools:
            try:
                llm_with_tools = self.llm_client.bind_tools(tools)
                result = await llm_with_tools.ainvoke(prompt_messages)
            except (NotImplementedError, AttributeError):
                # LLM doesn't support tool binding (e.g., test mock), fallback to regular invoke
                logger.debug(f"⚠️ LLM doesn't support tool binding, using regular invoke")
                result = await self.llm_client.ainvoke(prompt_messages)
        else:
            # No tools, use regular LLM invocation
            result = await self.llm_client.ainvoke(prompt_messages)

        logger.debug(f"📄 Result type: {type(result).__name__}, "
                    f"has tool_calls: {hasattr(result, 'tool_calls') and bool(getattr(result, 'tool_calls', None))}")
        
        # Add result to messages for potential tool processing
        state = self._process_step_completion(state, result)
        
        logger.info(f"✅ Step '{step_config.name}' completed (status: {step_state.status})")
            
        return state
    
    def _should_continue(self, state: WorkflowState) -> Literal["continue", "end", "tools"]:
        """Determine if workflow should continue to next step or end."""
        # last message should be an AI message
        if state.status in ["completed", "failed"]:
            logger.debug(f"🔚 Workflow ending: status={state.status}")
            return "end"
        else:
            logger.debug(f"➡️  Workflow continuing: step {state.current_step}/{len(state.step_configs)}")
            return "continue"
    
    def _route_after_step(self, state: WorkflowState) -> Literal["continue", "end", "tools"]:
        """Update state after step execution or make tool calls."""
        # If no tool calls, process workflow commands immediately
        result = state.messages[-1]
        has_tool_calls = hasattr(result, 'tool_calls') and bool(getattr(result, 'tool_calls', None))
        
        if not has_tool_calls:
            logger.debug(f"🚫 No tool calls found, routing to workflow continuation")
            return self._should_continue(state)
        else:
            logger.debug(f"🔧 Tool calls detected, routing to tools")
            return "tools"
        
    async def _route_request_node(self, state: WorkflowState) -> WorkflowState | dict[str, bool]:
        """Front-end routing node to determine if workflow is needed or direct response."""
        # If no workflow_responsibility is configured, always use workflow
        if not self.config.workflow_responsibility:
            return {
                "should_use_workflow": True
            }
        
        return_state = {}
        # Build routing prompt
        system_prompt = f"""You are a routing assistant. Determine if the user's request is relevant to this workflow's responsibility.

Workflow Responsibility: {self.config.workflow_responsibility}

Instructions:
1. If the request is relevant to the workflow's responsibility, respond with: WORKFLOW
2. If the request is a simple greeting, off-topic, or can be answered directly without the workflow, respond with: DIRECT

Then, if responding DIRECT, provide a brief, helpful response to the user.

Format your response as:
DECISION: [WORKFLOW or DIRECT]
RESPONSE: [your response if DIRECT, or "N/A" if WORKFLOW]
"""
        
        # Call LLM for routing decision
        system_message = SystemMessage(content=system_prompt)
        user_message = HumanMessage(content=state.input)
        # Use minimal history for routing context
        history_message = trim_messages(state.messages[-self.history_size:], strategy="last", max_tokens=1000, token_counter=count_tokens_approximately, start_on="human")

        messages = [system_message] + history_message + [user_message]
        
        logger.info(f"🔀 Routing request to determine if workflow is needed")
        result = await self.llm_client.ainvoke(messages)
        
        # Extract text content from result
        response_text = result.content
        
        # Ensure response_text is a string
        if isinstance(response_text, list):
            # Join list items if it's a list
            response_text = " ".join(str(item) for item in response_text)
        elif not isinstance(response_text, str):
            response_text = str(response_text)
        
        # Parse the response
        decision = "WORKFLOW"  # Default to workflow
        direct_response = ""
        
        lines = response_text.strip().split('\n')
        for line in lines:
            if line.startswith('DECISION:'):
                decision = line.split(':', 1)[1].strip().upper()
            elif line.startswith('RESPONSE:'):
                direct_response = line.split(':', 1)[1].strip()
            else:
                direct_response += line + "\n"
        
        if decision == "DIRECT" and direct_response and direct_response != "N/A":
            logger.info(f"✅ Routing decision: DIRECT response")
            if result.id:
                messages = [AIMessage(content=direct_response, id=result.id)]
            else:
                messages = [AIMessage(content=direct_response)]

            return_state = {
                "should_use_workflow": False,
                "response": direct_response,  # Store direct response in 'response' field
                "status": "completed",
                "messages": messages
            }
        else:
            logger.info(f"✅ Routing decision: WORKFLOW execution")
            return_state = {
                "should_use_workflow": True
            }

        return return_state
    
    async def _build_graph(self) -> CompiledStateGraph:
        """Build the workflow execution graph with optional routing and ToolNode for tool handling."""
        workflow = StateGraph(WorkflowState)
        
        # Get all possible tools for the workflow
        all_tool_names = []
        for step_config in self.workflow_step_configs:
            all_tool_names.extend(step_config.tools)
        all_tools = await self.get_tools(list(set(all_tool_names)))  # Remove duplicates
        
        # Add routing node if workflow_responsibility is configured
        has_routing = bool(self.config.workflow_responsibility and self.config.workflow_responsibility.strip())
        
        if has_routing:
            workflow.add_node("route_request", self._route_request_node)
            workflow.set_entry_point("route_request")
        
        # Add step execution node
        workflow.add_node("execute_step", self._execute_step_node)
        
        # Add tool node for handling tool calls
        if all_tools:
            tool_node = ToolNode(all_tools)
            workflow.add_node("tools", tool_node)
        
        # Set entry point (either routing or direct to execute_step)
        if not has_routing:
            workflow.set_entry_point("execute_step")
        
        # Add conditional routing from route_request if enabled
        if has_routing:
            workflow.add_conditional_edges(
                "route_request",
                lambda state: "execute_step" if state.should_use_workflow else "end",
                {
                    "execute_step": "execute_step",
                    "end": END
                }
            )
        
        # Add conditional routing after step execution
        if all_tools:
            workflow.add_conditional_edges(
                "execute_step",
                self._route_after_step,
                {
                    "tools": "tools",  # Route to tools if tool calls present
                    "continue": "execute_step",  # Continue to next step
                    "end": END  # End workflow
                }
            )

            # After tools, return to execute_step
            workflow.add_edge("tools", "execute_step")

        else:
            # No tools available, use simple routing
            workflow.add_conditional_edges(
                "execute_step",
                self._should_continue,
                {
                    "continue": "execute_step",  # Loop back to execute next step
                    "end": END
                }
            )
        
        return workflow.compile()
    
    def _create_initial_state(self, messages: list[ChatMessage]) -> WorkflowState:
        """Create initial workflow state."""
        # Initialize step states for all steps
        step_states = {}
        for step_config in self.workflow_step_configs:
            step_states[step_config.id] = WorkflowStepState(step_id=step_config.id)
        
        # Get the last user message as the input (most recent request)
        # This ensures we process the current user message, not the first one in history
        user_input = messages[-1].content if messages else ""
        
        return WorkflowState(
            input=user_input,
            step_configs=self.workflow_step_configs,
            step_states=step_states,
            messages=self._convert_to_langgraph_messages(messages[-self.history_size:-1])
        )

    @override
    async def _extract_final_content(self, final_state: dict[str, Any]) -> str:
        """Extract content from workflow execution result."""
        state = WorkflowState.model_validate(final_state)
        
        # If we have a response (either from routing or last step), return it
        if state.response:
            return state.response
        
        # Otherwise, return workflow execution summary
        result_lines = [
            "Workflow Execution Summary:",
            f"Status: {state.status}",
            f"Completed Steps: {state.completed_steps}/{len(state.step_configs)}",
            f"Failed Steps: {state.failed_steps}",
            "",
            "Step Results:"
        ]

        for step_config in state.step_configs:
            step_state = state.step_states.get(step_config.id)

            if step_state:
                status_icon = {
                    StepResult.SUCCESS: "✅",
                    StepResult.FAILED: "❌",
                    StepResult.SKIPPED: "⏭️",
                    StepResult.ERROR: "⚠️",
                    None: "⏳"
                }.get(step_state.result)
                
                result_lines.append(f"{status_icon} {step_config.name}: {step_state.status}")
                if step_state.result_content:
                    result_lines.append(f"   Result: {step_state.result_content}")
                if step_state.error:
                    result_lines.append(f"   Error: {step_state.error}")
            else:
                # Step not executed yet
                result_lines.append(f"⏳ {step_config.name}: Not started")
        
        return "\n".join(result_lines)

    @override
    async def _process_state_update(
        self, 
        state_update: dict[str, Any], 
        chunk_index: int = 0,
        metadata: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Process state updates for workflow agent.
        
        This workflow agent streams progress as each step executes.
        State updates contain the workflow state with current step information.
        """
        
        # Extract workflow state from state updates
        # State updates are dictionaries where keys are node names
        for node_name, node_state in state_update.items():
            logger.debug(f"🔄 Processing workflow node '{node_name}' with update: {node_state}")

            # direct_response case (from routing node)
            if node_name == "route_request" and isinstance(node_state, dict):
                should_use_workflow = node_state.get("should_use_workflow", True)
                response = node_state.get("response")
                
                if response:
                    content = f"{response}\n"
                    yield StreamingChunk(
                        content=content,
                        finish_reason="stop",
                        metadata={
                            'template_id': self.template_id,
                            'framework': 'langgraph',
                            'stream_mode': 'updates',
                            'chunk_index': chunk_index,
                            'node': node_name,
                            'should_use_workflow': should_use_workflow
                        }
                    )
                
                if not should_use_workflow:
                    return  # End streaming as workflow is not used
            
            # Check if this is our workflow state
            if isinstance(node_state, dict):
                current_step = node_state.get("current_step")
                step_configs: Optional[list[WorkflowStepConfig]] = node_state.get("step_configs")
                step_states: dict[str, WorkflowStepState]= node_state.get("step_states", {})
                final_status = node_state.get("status", "")
                
                if step_configs and step_states and current_step:
                    step_config = step_configs[current_step]
                    step_state = step_states.get(step_config.id)
                    
                    # Generate progress message based on step status
                    if step_state:
                        status = step_state.status
                        step_name = step_config.name

                        if status == StepStatus.RUNNING or status == StepStatus.PENDING:
                            content = f"🔄 Executing {step_name}...\n"
                        elif status == StepStatus.COMPLETED:
                            content = f"✅ {step_name}: Completed\n"
                        else:
                            content = ""
                        
                        if content:
                            yield StreamingChunk(
                                content=content,
                                finish_reason=None,
                                metadata={
                                    'template_id': self.template_id,
                                    'framework': 'langgraph',
                                    'stream_mode': 'updates',
                                    'chunk_index': chunk_index,
                                    'node': node_name,
                                    'step_name': step_name,
                                    'step_status': status,
                                    'current_step': current_step,
                                    'total_steps': len(step_configs)
                                }
                            )
                    
                    if final_status in ["completed", "failed"]:
                        # Final completion message
                        final_content = await self._extract_final_content(node_state)
                        # yield the final content in parts to make the client render progressively
                        while final_content:
                            # Extract up to 100 chars
                            chunk = final_content[:100]
                            final_content = final_content[100:]
                            
                            yield StreamingChunk(
                                content=chunk,
                                finish_reason=None,
                                metadata={
                                    'template_id': self.template_id,
                                    'framework': 'langgraph',
                                    'stream_mode': 'updates', 
                                    'chunk_index': chunk_index,
                                    'node': node_name,
                                    'final_status': final_status
                                }
                            )

                        return  # End streaming as workflow is done
            
    

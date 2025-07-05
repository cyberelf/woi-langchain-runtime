"""Pydantic models for API requests and responses."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from runtime.generated import TemplateConfigSchema


class MessageRole(str, Enum):
    """Message roles in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FinishReason(str, Enum):
    """Completion finish reasons."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    ERROR = "error"


# Agent Management Models


class ConversationConfig(BaseModel):
    """Conversation configuration."""

    continuous: bool = Field(default=True, description="Enable continuous conversation mode")
    historyLength: int = Field(default=10, ge=5, le=100, description="Maximum conversation history length")


class TaskStepsConfig(BaseModel):
    """Task steps configuration."""

    steps: list[str] = Field(..., min_length=1, max_length=20, description="List of task execution steps")
    stepTimeout: int = Field(default=300, ge=10, le=3600, description="Timeout for each step in seconds")
    retryCount: int = Field(default=2, ge=0, le=5, description="Number of retries on step failure")
    parallelExecution: bool = Field(default=False, description="Allow parallel step execution")


class ValidationConfig(BaseModel):
    """Validation configuration."""

    strictMode: bool = Field(default=True, description="Enable strict validation mode")
    outputFormat: str = Field(default="structured", description="Output format")


class CodeSourceConfig(BaseModel):
    """Code source configuration for custom agents."""

    type: str = Field(..., description="Code type: inline, repository, or package")
    content: str = Field(..., description="Code content or reference")
    entryPoint: str = Field(default="main", description="Code execution entry point")
    dependencies: list[str] = Field(default_factory=list, description="Required dependencies")


class RuntimeConfig(BaseModel):
    """Runtime configuration for custom agents."""

    language: str = Field(..., description="Programming language")
    version: Optional[str] = Field(default=None, description="Language version")
    timeout: int = Field(default=30, ge=1, le=300, description="Execution timeout in seconds")
    memoryLimit: int = Field(default=512, ge=64, le=2048, description="Memory limit in MB")


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent."""

    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    type: str = Field(..., description="Agent type/template_id")
    template_id: str = Field(..., description="Template identifier")
    template_version_id: str = Field(..., description="Template version identifier")
    template_config: dict[str, Any] = Field(
        default_factory=dict, description="Template-specific configuration"
    )
    system_prompt: str = Field(..., description="System prompt for the agent")
    conversation_config: Optional[ConversationConfig] = Field(
        default=None, description="Conversation configuration"
    )
    toolsets: list[str] = Field(default_factory=list, description="Selected toolsets")
    llm_config_id: str = Field(..., description="LLM configuration identifier")


class ValidationResult(BaseModel):
    """Validation result."""

    valid: bool = Field(..., description="Whether validation passed")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class AgentResponse(BaseModel):
    """Response model for agent operations."""

    success: bool = Field(..., description="Operation success status")
    agent_id: str = Field(..., description="Agent identifier")
    message: str = Field(..., description="Response message")
    validation_results: Optional[ValidationResult] = Field(default=None, description="Validation results")


# OpenAI Compatible Models


class ChatMessage(BaseModel):
    """Chat message in OpenAI format."""

    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = Field(..., description="Agent ID to execute")
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    stream: bool = Field(default=False, description="Whether to stream the response")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional execution metadata")


class ChatChoice(BaseModel):
    """Chat completion choice."""

    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Generated message")
    finish_reason: FinishReason = Field(..., description="Completion finish reason")


class ChatUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(..., description="Number of prompt tokens")
    completion_tokens: int = Field(..., description="Number of completion tokens")
    total_tokens: int = Field(..., description="Total number of tokens")


class ExecutionStep(BaseModel):
    """Agent execution step information."""

    step: str = Field(..., description="Step name")
    status: str = Field(..., description="Step status")
    duration_ms: int = Field(..., description="Step duration in milliseconds")


class ChatCompletionMetadata(BaseModel):
    """Extended metadata for chat completion."""

    agent_id: str = Field(..., description="Agent identifier")
    agent_type: str = Field(..., description="Agent type")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    execution_steps: list[ExecutionStep] = Field(default_factory=list, description="Execution steps")
    tools_used: list[str] = Field(default_factory=list, description="Tools used during execution")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score")


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str = Field(..., description="Completion ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model/agent ID")
    choices: list[ChatChoice] = Field(..., description="Completion choices")
    usage: ChatUsage = Field(..., description="Token usage")
    metadata: Optional[ChatCompletionMetadata] = Field(default=None, description="Extended metadata")


class ChatCompletionChunk(BaseModel):
    """Streaming chat completion chunk."""

    id: str = Field(..., description="Completion ID")
    object: str = Field(default="chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model/agent ID")
    choices: list[dict[str, Any]] = Field(..., description="Streaming choices")
    usage: Optional[ChatUsage] = Field(default=None, description="Token usage (final chunk only)")


# Schema Models
class RuntimeRequirements(BaseModel):
    """Runtime requirements for agent template."""

    memory: str = Field(..., description="Memory requirement")
    cpu: str = Field(..., description="CPU requirement")
    gpu: bool = Field(..., description="GPU requirement")
    estimatedLatency: str = Field(..., description="Estimated latency")


class LLMConfig(BaseModel):
    """LLM configuration."""

    provider: Literal["openai", "google", "deepseek"] = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional execution metadata")

class AgentTemplate(BaseModel):
    """Agent template definition."""

    template_name: str = Field(..., description="Template name")
    template_id: str = Field(..., description="Template identifier")
    template_type: str = Field(..., description="Template type")
    version: str = Field(..., description="Template version")
    configSchema: TemplateConfigSchema = Field(..., description="Configuration schema")


class RuntimeCapabilities(BaseModel):
    """Runtime capabilities."""

    streaming: bool = Field(default=True, description="Streaming support")
    toolCalling: bool = Field(default=True, description="Tool calling support")
    multimodal: bool = Field(default=False, description="Multimodal support")
    codeExecution: bool = Field(default=True, description="Code execution support")


class RuntimeLimits(BaseModel):
    """Runtime limits."""

    maxConcurrentAgents: int = Field(..., description="Maximum concurrent agents")
    maxMessageLength: int = Field(..., description="Maximum message length")
    maxConversationHistory: int = Field(..., description="Maximum conversation history")


class SchemaResponse(BaseModel):
    """Runtime schema response."""

    version: str = Field(..., description="Schema version")
    lastUpdated: str = Field(..., description="Last update timestamp")
    supportedAgentTemplates: list[AgentTemplate] = Field(..., description="Supported agent templates")
    capabilities: RuntimeCapabilities = Field(..., description="Runtime capabilities")
    limits: RuntimeLimits = Field(..., description="Runtime limits")


# Health Check Models


class HealthCheckItem(BaseModel):
    """Individual health check item."""

    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional details")


class HealthMetrics(BaseModel):
    """Health metrics."""

    uptime_seconds: int = Field(..., description="Uptime in seconds")
    total_agents: int = Field(..., description="Total number of agents")
    active_agents: int = Field(..., description="Number of active agents")
    templates_loaded: int = Field(..., description="Number of templates loaded")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="Runtime version")
    checks: list[HealthCheckItem] = Field(..., description="Individual health checks")
    metrics: HealthMetrics = Field(..., description="Runtime metrics")


# Error Models


class ErrorDetail(BaseModel):
    """Error detail information."""

    field: Optional[str] = Field(default=None, description="Field with error")
    code: str = Field(..., description="Error code")
    additional_info: Optional[str] = Field(default=None, description="Additional error information")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    details: Optional[str] = Field(default=None, description="Error details")

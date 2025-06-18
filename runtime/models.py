"""Pydantic models for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Agent types supported by the runtime."""
    CONVERSATION = "conversation"
    TASK = "task"
    CUSTOM = "custom"


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
    steps: List[str] = Field(..., min_items=1, max_items=20, description="List of task execution steps")
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
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")


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
    type: AgentType = Field(..., description="Agent type")
    template_id: str = Field(..., description="Template identifier")
    template_version_id: str = Field(..., description="Template version identifier")
    template_config: Dict[str, Any] = Field(default_factory=dict, description="Template-specific configuration")
    system_prompt: str = Field(..., description="System prompt for the agent")
    conversation_config: Optional[ConversationConfig] = Field(default=None, description="Conversation configuration")
    toolsets: List[str] = Field(default_factory=list, description="Selected toolsets")
    llm_config_id: str = Field(..., description="LLM configuration identifier")


class ValidationResult(BaseModel):
    """Validation result."""
    valid: bool = Field(..., description="Whether validation passed")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


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
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    stream: bool = Field(default=False, description="Whether to stream the response")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional execution metadata")


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
    agent_type: AgentType = Field(..., description="Agent type")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    execution_steps: List[ExecutionStep] = Field(default_factory=list, description="Execution steps")
    tools_used: List[str] = Field(default_factory=list, description="Tools used during execution")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score")


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str = Field(..., description="Completion ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model/agent ID")
    choices: List[ChatChoice] = Field(..., description="Completion choices")
    usage: ChatUsage = Field(..., description="Token usage")
    metadata: Optional[ChatCompletionMetadata] = Field(default=None, description="Extended metadata")


class ChatCompletionChunk(BaseModel):
    """Streaming chat completion chunk."""
    id: str = Field(..., description="Completion ID")
    object: str = Field(default="chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model/agent ID")
    choices: List[Dict[str, Any]] = Field(..., description="Streaming choices")
    usage: Optional[ChatUsage] = Field(default=None, description="Token usage (final chunk only)")


# Schema Models

class FieldValidation(BaseModel):
    """Field validation rules."""
    min: Optional[int] = Field(default=None, description="Minimum value")
    max: Optional[int] = Field(default=None, description="Maximum value")
    minItems: Optional[int] = Field(default=None, description="Minimum array items")
    maxItems: Optional[int] = Field(default=None, description="Maximum array items")
    pattern: Optional[str] = Field(default=None, description="Regex pattern")


class ConfigField(BaseModel):
    """Configuration field definition."""
    id: str = Field(..., description="Field identifier")
    type: str = Field(..., description="Field type")
    label: str = Field(..., description="Field label")
    description: str = Field(..., description="Field description")
    defaultValue: Optional[Any] = Field(default=None, description="Default value")
    validation: Optional[FieldValidation] = Field(default=None, description="Validation rules")


class ConfigSection(BaseModel):
    """Configuration section definition."""
    id: str = Field(..., description="Section identifier")
    title: str = Field(..., description="Section title")
    description: str = Field(..., description="Section description")
    fields: List[ConfigField] = Field(..., description="Section fields")


class AgentTemplateSchema(BaseModel):
    """Agent template schema definition."""
    template_name: str = Field(..., description="Template name")
    template_id: str = Field(..., description="Template identifier")
    sections: List[ConfigSection] = Field(..., description="Configuration sections")


class RuntimeRequirements(BaseModel):
    """Runtime requirements for agent template."""
    memory: str = Field(..., description="Memory requirement")
    cpu: str = Field(..., description="CPU requirement")
    gpu: bool = Field(..., description="GPU requirement")
    estimatedLatency: str = Field(..., description="Estimated latency")


class AgentTemplate(BaseModel):
    """Agent template definition."""
    template_name: str = Field(..., description="Template name")
    template_id: str = Field(..., description="Template identifier")
    version: str = Field(..., description="Template version")
    configSchema: AgentTemplateSchema = Field(..., description="Configuration schema")
    runtimeRequirements: RuntimeRequirements = Field(..., description="Runtime requirements")


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
    supportedAgentTemplates: List[AgentTemplate] = Field(..., description="Supported agent templates")
    capabilities: RuntimeCapabilities = Field(..., description="Runtime capabilities")
    limits: RuntimeLimits = Field(..., description="Runtime limits")


# Health Check Models

class HealthCheckItem(BaseModel):
    """Individual health check item."""
    status: str = Field(..., description="Health status")
    response_time_ms: Optional[int] = Field(default=None, description="Response time in milliseconds")
    last_check: str = Field(..., description="Last check timestamp")
    loaded_templates: Optional[int] = Field(default=None, description="Number of loaded templates")


class HealthMetrics(BaseModel):
    """Health metrics."""
    active_agents: int = Field(..., description="Number of active agents")
    total_executions: int = Field(..., description="Total executions")
    average_response_time_ms: int = Field(..., description="Average response time")
    error_rate: float = Field(..., description="Error rate")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="Runtime version")
    uptime_seconds: int = Field(..., description="Uptime in seconds")
    last_sync: Optional[str] = Field(default=None, description="Last sync timestamp")
    checks: Dict[str, HealthCheckItem] = Field(..., description="Individual health checks")
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
    details: Optional[ErrorDetail] = Field(default=None, description="Error details") 
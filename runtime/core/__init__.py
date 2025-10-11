"""Core foundational components for the Agent Runtime framework.

This module provides truly foundational, dependency-free components:
- Core interfaces and abstractions
- Base exception classes
- Fundamental type definitions

Components that depend on other layers have been moved to:
- Orchestration: runtime.orchestration (AgentFactory, AgentScheduler)
- Templates: runtime.templates
- Toolsets: runtime.toolsets
"""

from .interfaces import (
    Initializable,
    HealthCheckable,
    Configurable,
    BaseService,
    BaseRepository,
    BaseManager,
)
from .exceptions import (
    RuntimeError,
    ConfigurationError,
    InitializationError,
    ValidationError,
    NotFoundError,
    ConflictError,
    ServiceUnavailableError,
    TimeoutError,
)
from .types import (
    AgentId,
    TaskId,
    ContextId,
    TemplateId,
    ToolsetId,
    UserId,
    ComponentStatus,
    LogLevel,
    Environment,
    ConfigDict,
    MetadataDict,
    HeadersDict,
    QueryParams,
    HealthStatus,
    HealthMetrics,
    PaginationParams,
    PaginatedResult,
    ErrorDetails,
    ErrorResponse,
)

__all__ = [
    # Interfaces
    "Initializable",
    "HealthCheckable", 
    "Configurable",
    "BaseService",
    "BaseRepository",
    "BaseManager",
    # Exceptions
    "RuntimeError",
    "ConfigurationError",
    "InitializationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ServiceUnavailableError",
    "TimeoutError",
    # Types
    "AgentId",
    "TaskId",
    "ContextId",
    "TemplateId",
    "ToolsetId", 
    "UserId",
    "ComponentStatus",
    "LogLevel",
    "Environment",
    "ConfigDict",
    "MetadataDict",
    "HeadersDict",
    "QueryParams",
    "HealthStatus",
    "HealthMetrics",
    "PaginationParams",
    "PaginatedResult",
    "ErrorDetails",
    "ErrorResponse",
]
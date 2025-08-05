"""Core type definitions for the Agent Runtime framework.

This module defines fundamental types, enums, and type aliases that are
used throughout the runtime system. These provide type safety and
clear semantics for core concepts.
"""

from enum import Enum
from typing import Any, Dict, List, NewType, Optional, Union
from uuid import UUID


# Core ID types for type safety
AgentId = NewType("AgentId", str)
SessionId = NewType("SessionId", str) 
TemplateId = NewType("TemplateId", str)
ToolsetId = NewType("ToolsetId", str)
UserId = NewType("UserId", str)


class ComponentStatus(str, Enum):
    """Status of runtime components."""
    
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    ERROR = "error"
    STOPPED = "stopped"


class LogLevel(str, Enum):
    """Logging levels."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Runtime environments."""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# Type aliases for common patterns
ConfigDict = Dict[str, Any]
MetadataDict = Dict[str, Any]
HeadersDict = Dict[str, str]
QueryParams = Dict[str, Union[str, int, float, bool]]

# Health check types
HealthStatus = Dict[str, Any]
HealthMetrics = Dict[str, Union[int, float, str]]

# Pagination types
PaginationParams = Dict[str, Union[int, str]]
PaginatedResult = Dict[str, Any]

# Error response types
ErrorDetails = Dict[str, Any]
ErrorResponse = Dict[str, Union[str, int, ErrorDetails]]
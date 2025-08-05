"""Core exception classes for the Agent Runtime framework.

This module defines the foundational exception hierarchy that all other
layers can use and extend. These exceptions provide clear error semantics
throughout the runtime system.
"""

from typing import Any, Dict, Optional


class RuntimeError(Exception):
    """Base exception for all runtime errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "RUNTIME_ERROR"
        self.details = details or {}


class ConfigurationError(RuntimeError):
    """Raised when there's a configuration problem."""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key


class InitializationError(RuntimeError):
    """Raised when component initialization fails."""
    
    def __init__(
        self, 
        message: str, 
        component: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "INITIALIZATION_ERROR", details)
        self.component = component


class ValidationError(RuntimeError):
    """Raised when validation fails."""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


class NotFoundError(RuntimeError):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self, 
        message: str, 
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "NOT_FOUND_ERROR", details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictError(RuntimeError):
    """Raised when there's a resource conflict."""
    
    def __init__(
        self, 
        message: str, 
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "CONFLICT_ERROR", details)
        self.resource_type = resource_type


class ServiceUnavailableError(RuntimeError):
    """Raised when a service is unavailable."""
    
    def __init__(
        self, 
        message: str, 
        service: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "SERVICE_UNAVAILABLE_ERROR", details)
        self.service = service


class TimeoutError(RuntimeError):
    """Raised when an operation times out."""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "TIMEOUT_ERROR", details)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
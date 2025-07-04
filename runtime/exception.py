"""
Exception handlers for the runtime API.
"""

from fastapi import HTTPException, Request
from runtime.models import ErrorResponse
from runtime.config import settings


# Exception handler functions that can be registered with the main FastAPI app
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return ErrorResponse(
        error="HTTP_ERROR",
        message=exc.detail,
        status_code=exc.status_code,
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    return ErrorResponse(
        error="INTERNAL_ERROR",
        message="An internal server error occurred",
        details=str(exc) if settings.debug else None,
    ) 
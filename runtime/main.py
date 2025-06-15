"""Main FastAPI application for the LangChain Agent Runtime."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .config import settings
from . import __version__


# Configure structured logging
def configure_logging() -> None:
    """Configure structured logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    configure_logging()
    logger = structlog.get_logger()
    
    logger.info(
        "Starting LangChain Agent Runtime",
        version=__version__,
        host=settings.host,
        port=settings.port,
        debug=settings.debug
    )
    
    # Initialize any startup tasks here
    # For example, warming up LLM connections, loading models, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down LangChain Agent Runtime")
    
    # Cleanup tasks here
    # For example, closing database connections, saving state, etc.


# Create FastAPI application
app = FastAPI(
    title="LangChain Agent Runtime",
    description="LangChain/LangGraph Agent Runtime Service for AI Platform",
    version=__version__,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "service": "LangChain Agent Runtime",
        "version": __version__,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled"
    }


@app.get("/ping")
async def ping() -> dict:
    """Simple ping endpoint for basic health checks."""
    return {"status": "ok", "message": "pong"}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger = structlog.get_logger()
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An internal server error occurred",
            "details": None
        }
    )


def run_server() -> None:
    """Run the server."""
    uvicorn.run(
        "runtime.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    run_server() 
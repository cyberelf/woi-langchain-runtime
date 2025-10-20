"""DDD-compliant main application with async task management - Infrastructure layer."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routes import agent_routes, execution_routes, template_routes
from .dependencies import startup_dependencies, shutdown_dependencies, get_architecture_info
from .auth import runtime_auth

# Logging is configured in main.py - don't override it here
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with task management initialization."""
    # Startup
    logger.info("Starting Agent Runtime with async task management...")
    
    try:
        # Initialize plugin system
        from runtime.core.plugin import initialize_plugin_system
        await initialize_plugin_system()
        logger.info("Plugin system initialized")
        
        # Initialize new task management architecture
        dependencies = await startup_dependencies()
        logger.info("Task management architecture initialized successfully")
        
        # Store dependencies in app state for health checks
        app.state.dependencies = dependencies
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Runtime...")
    try:
        await shutdown_dependencies()
        logger.info("Task management architecture shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Agent Runtime API",
        description="Agent runtime service with async task management",
        version="2.1.0",
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
    
    # Include routers
    app.include_router(agent_routes.router)
    app.include_router(execution_routes.router)
    app.include_router(template_routes.router)
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "Agent Runtime Service",
            "version": "2.1.0",
            "architecture": "DDD + Async Task Management",
            "features": get_architecture_info()["features"]
        }
    
    @app.get("/ping")
    async def ping():
        """Ping endpoint."""
        return {
            "status": "ok",
            "message": "pong",
            "architecture": "async_task_management"
        }
    
    @app.get("/v1/health")
    async def health_check(_: bool = Depends(runtime_auth)):
        """Health check endpoint with task management status."""
        base_health = {
            "status": "healthy",
            "version": "2.1.0",
            "architecture": "DDD + Async Task Management",
            "timestamp": "2024-03-20T10:00:00Z",
            "orchestrator": {
                "running": False,
                "workers": 0,
                "active_instances": 0,
                "running_messages": 0
            }
        }
        
        # Add architecture info
        base_health.update(get_architecture_info())
        
        # Add orchestrator health if available
        if hasattr(app.state, 'dependencies'):
            deps = app.state.dependencies
            if 'orchestrator' in deps:
                orchestrator = deps['orchestrator']
                base_health['orchestrator'] = {
                    "running": orchestrator._running,
                    "workers": len(orchestrator._message_workers),
                    "active_instances": len(orchestrator._agent_instances),
                    "running_messages": len(orchestrator._running_messages)
                }
        
        return base_health
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
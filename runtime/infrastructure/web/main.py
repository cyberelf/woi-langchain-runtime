"""DDD-compliant main application with async task management - Infrastructure layer."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routes import agent_routes, execution_routes, template_routes
from .dependencies import startup_dependencies, shutdown_dependencies, get_architecture_info
from ...auth import runtime_auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with task management initialization."""
    # Startup
    logger.info("Starting Agent Runtime with async task management...")
    
    try:
        # Initialize new task management architecture
        dependencies = await startup_dependencies()
        logger.info("Task management architecture initialized successfully")
        
        # Store dependencies in app state for health checks
        app.state.dependencies = dependencies
        
    except Exception as e:
        logger.error(f"Failed to initialize task management: {e}")
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
            "timestamp": "2024-03-20T10:00:00Z"
        }
        
        # Add architecture info
        base_health.update(get_architecture_info())
        
        # Add task manager health if available
        if hasattr(app.state, 'dependencies'):
            deps = app.state.dependencies
            if 'task_manager' in deps:
                task_manager = deps['task_manager']
                base_health['task_manager'] = {
                    "running": task_manager._running,
                    "workers": len(task_manager._task_workers),
                    "active_instances": len(task_manager._agent_instances),
                    "running_tasks": len(task_manager._running_tasks)
                }
        
        return base_health
    
    @app.get("/v1/schema")
    async def get_schema(_: bool = Depends(runtime_auth)):
        """Get runtime schema endpoint."""
        return {
            "version": "2.1.0",
            "lastUpdated": "2024-03-20T10:00:00Z",
            "architecture": "async_task_management",
            "supportedAgentTemplates": [
                {
                    "template_name": "智能客服助手",
                    "template_id": "customer-service-bot",
                    "version": "1.0.0",
                    "type": "conversation",
                    "configSchema": {
                        "template_name": "智能客服助手",
                        "template_id": "customer-service-bot",
                        "sections": [
                            {
                                "id": "conversation",
                                "title": "对话设置",
                                "description": "配置智能体的对话行为",
                                "fields": [
                                    {
                                        "id": "continuous",
                                        "type": "checkbox",
                                        "label": "持续对话模式",
                                        "description": "启用持续对话以保持上下文连贯性",
                                        "defaultValue": True
                                    },
                                    {
                                        "id": "historyLength",
                                        "type": "number",
                                        "label": "对话历史长度",
                                        "description": "保留的最大历史消息数量",
                                        "defaultValue": 10,
                                        "validation": {
                                            "min": 5,
                                            "max": 100
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ],
            "capabilities": {
                "streaming": True,
                "toolCalling": True,
                "multimodal": False,
                "codeExecution": True,
                "sessionManagement": True,
                "asyncExecution": True,
                "horizontalScaling": True
            },
            "limits": {
                "maxConcurrentAgents": 100,
                "maxMessageLength": 32000,
                "maxConversationHistory": 100,
                "maxTaskWorkers": 50,
                "sessionTimeoutSeconds": 7200
            }
        }
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
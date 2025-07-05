"""Main application entry point for LangChain Agent Runtime."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from runtime.api import router as api_router
from runtime.config import settings
from runtime.core import AgentFactory, AgentScheduler, TemplateManager
from runtime.exception import general_exception_handler, http_exception_handler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Main agent runtime service."""

    def __init__(self):
        # Core components
        self.template_manager = TemplateManager()
        self.agent_factory = AgentFactory(self.template_manager)
        self.scheduler = AgentScheduler(self.agent_factory)

        # Runtime state
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize the runtime and all components."""
        if self.initialized:
            return

        try:
            logger.info("Initializing Agent Runtime...")

            # Initialize template manager
            await self.template_manager.initialize()
            logger.info(f"Loaded {len(self.template_manager.list_templates())} templates")

            # Start scheduler
            await self.scheduler.start()
            logger.info("Agent scheduler started")

            self.initialized = True
            logger.info("Agent Runtime initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize runtime: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the runtime and cleanup resources."""
        if not self.initialized:
            return

        try:
            logger.info("Shutting down Agent Runtime...")

            # Stop scheduler
            await self.scheduler.stop()

            # Cleanup factory
            self.agent_factory.cleanup_all()

            self.initialized = False
            logger.info("Agent Runtime shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def get_health_status(self) -> dict:
        """Get runtime health status."""
        try:
            template_count = len(self.template_manager.list_templates())
            scheduler_stats = self.scheduler.get_stats()
            factory_stats = self.agent_factory.get_stats()

            return {
                "status": "healthy" if self.initialized else "not_initialized",
                "templates_loaded": template_count,
                "total_agents": factory_stats["total_agents"],
                "active_agents": scheduler_stats.get("active_agents", 0),
                "initialized": self.initialized,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "initialized": self.initialized,
            }


# Global runtime instance
runtime = AgentRuntime()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await runtime.initialize()

    # Inject runtime into app state for API access
    app.state.runtime = runtime

    yield

    # Shutdown
    await runtime.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LangChain Agent Runtime",
        description="A LangChain/LangGraph-based agent runtime service",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router)

    # Register exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Add simple health check endpoints
    @app.get("/ping")
    async def ping():
        """Simple ping endpoint."""
        return {"status": "ok", "message": "pong"}

    @app.get("/health")
    async def health():
        """Comprehensive health check."""
        return runtime.get_health_status()

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "runtime.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

#!/usr/bin/env python3
"""Main entry point for Agent Runtime - Clean DDD Implementation.

This is the primary entry point for the LangChain Agent Runtime using
Domain-Driven Design architecture. All legacy compatibility has been removed.

Architecture:
    📚 Domain Layer: Pure business logic, entities, value objects
    🎭 Application Layer: Use cases, commands, queries  
    🏗️ Infrastructure Layer: Web, persistence, frameworks

Usage:
    python runtime/main.py                 # Start the server
    uvicorn runtime.main:app --reload      # Start with auto-reload
"""

import logging
import uvicorn

from runtime.infrastructure.web.main import create_app
from runtime.settings import settings

# Configure logging - debug setting controls log level
effective_level = settings.effective_log_level
logging.basicConfig(
    level=getattr(logging, effective_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True  # Override any existing logging configuration
)

logger = logging.getLogger(__name__)
logger.info(f"🔧 Logging configured: debug={settings.debug}, level={effective_level}")

# Create the DDD-compliant FastAPI app
app = create_app()

def main():
    """Run the Agent Runtime server."""
    logger.info("🚀 Starting Agent Runtime with DDD Architecture")
    logger.info("📚 Domain: Pure business logic, zero dependencies")
    logger.info("🎭 Application: Use cases and transaction boundaries")
    logger.info("🏗️ Infrastructure: External concerns properly isolated")
    logger.info("🎯 API Endpoints: /v1/agents, /health, /docs")
    logger.info(f"🌐 Server: http://{settings.host}:{settings.port}")
    
    uvicorn.run(
        "runtime.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.effective_log_level.lower(),
    )

if __name__ == "__main__":
    main()
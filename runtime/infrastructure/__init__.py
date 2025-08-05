"""Infrastructure layer - External concerns and implementations.

This layer contains:
- Concrete Repositories: Data persistence implementations
- Concrete Unit of Work: Transaction management implementations
- Web Layer: FastAPI routes and HTTP concerns
- Persistence: Database models and connections
- External Services: Third-party integrations
- Framework Integrations: LangGraph, etc.

The infrastructure layer provides concrete implementations for all
domain and application interfaces. It depends on both application
and domain layers.
"""

# This will be populated as we move infrastructure components
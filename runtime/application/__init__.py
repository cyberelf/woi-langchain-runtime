"""Application layer - Use cases and orchestration.

This layer contains:
- Application Services: Use case implementations
- Commands: Intent to change system state
- Queries: Intent to read system state  
- Handlers: Command and query processors

The application layer orchestrates domain objects to fulfill use cases.
It depends only on the domain layer and defines transaction boundaries.
"""

# This will be populated as we create application services
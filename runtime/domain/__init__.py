"""Domain layer - Pure business logic without external dependencies.

This layer contains:
- Entities: Domain objects with identity and behavior
- Value Objects: Immutable objects without identity
- Domain Services: Business logic that spans multiple entities
- Repository Interfaces: Contracts for data persistence
- Unit of Work Interfaces: Contracts for transaction management
- Domain Events: Business events that occur in the domain

The domain layer has NO dependencies on other layers and is completely
framework-agnostic. It represents the core business logic.
"""

# This will be populated as we move components
# New Layered Architecture

## Overview

This document describes the complete architectural refactoring that separates concerns into proper layers and fixes the OpenAI compatibility issues.

## Architecture Layers

### 1. API Layer (`runtime/api/`)

**Purpose**: Handle HTTP requests/responses and API contracts

**Components**:
- **Routes** (`runtime/api/routes/`):
  - `agent_routes.py` - Agent CRUD operations (`/v1/agents`)
  - `chat_routes.py` - Chat completion API (`/v1/chat/completions`)
  - `health_routes.py` - Health check endpoints (`/v1/health`)

- **Models** (`runtime/api/models/`):
  - `requests.py` - Request DTOs (ChatCompletionRequest, AgentCreateRequest)
  - `responses.py` - Response DTOs (ChatCompletionResponse, AgentResponse, etc.)

**Key Features**:
- ✅ **OpenAI Compatible**: `session_id` and `user_id` in metadata field
- ✅ **Proper DTOs**: Clear separation between API models and domain models
- ✅ **Route Organization**: Modular route structure for maintainability

### 2. Service Layer (`runtime/services/`)

**Purpose**: Business logic and orchestration

**Components**:
- `AgentConfigurationService` - Manages agent configurations
- `SessionService` - Handles chat sessions and conversation history

**Responsibilities**:
- ✅ **Business Rules**: Configuration validation, session lifecycle
- ✅ **Orchestration**: Coordinates between repositories and domain entities
- ✅ **Transaction Management**: Ensures data consistency

### 3. Domain Layer (`runtime/domain/`)

**Purpose**: Core business concepts and rules

**Components**:
- **Entities** (`runtime/domain/entities/`):
  - `AgentConfiguration` - Agent configuration aggregate
  - `ChatSession` - Chat session aggregate with conversation history

- **Value Objects** (`runtime/domain/value_objects/`):
  - `ChatMessage` - Immutable message representation
  - `MessageRole` - Message role enumeration  
  - `FinishReason` - Completion finish reason enumeration

**Key Features**:
- ✅ **Domain Logic**: Business rules encapsulated in entities
- ✅ **Immutability**: Value objects are immutable
- ✅ **Rich Models**: Entities contain behavior, not just data

### 4. Repository Layer (`runtime/repositories/`)

**Purpose**: Data access abstraction

**Components**:
- `AgentConfigurationRepository` - Abstract interface
- `InMemoryAgentConfigurationRepository` - In-memory implementation
- `SessionRepository` - Abstract interface  
- `InMemorySessionRepository` - In-memory implementation

**Benefits**:
- ✅ **Abstraction**: Business logic independent of storage
- ✅ **Testability**: Easy to mock for unit tests
- ✅ **Flexibility**: Can swap implementations (DB, cache, etc.)

### 5. Core Runtime Layer (`runtime/core/`)

**Purpose**: Agent execution and template management

**Components**:
- `TemplateManager` - Template discovery and management
- `AgentFactory` - Runtime agent instance creation
- `AgentScheduler` - Agent lifecycle management

**Integration**:
- ✅ **Separation**: Runtime logic separate from API logic
- ✅ **Auto-instantiation**: Creates agents from configurations on-demand
- ✅ **Template System**: Framework-agnostic agent templates

### 6. Infrastructure Layer (`runtime/infrastructure/`)

**Purpose**: External dependencies and cross-cutting concerns

**Future Components**:
- Database connections
- External service clients
- Caching implementations
- Message queues

## Key Architectural Principles

### 1. **Separation of Concerns**
```
API Layer       → HTTP/REST concerns
Service Layer   → Business logic
Domain Layer    → Core business concepts  
Repository Layer → Data access
Core Layer      → Agent runtime logic
Infrastructure  → External dependencies
```

### 2. **Dependency Direction**
```
API → Service → Domain ← Repository
     ↓                    ↑
   Core ←── Infrastructure
```

### 3. **OpenAI Compatibility**
```json
{
  "model": "agent-123",
  "messages": [...],
  "metadata": {
    "session_id": "session-456",
    "user_id": "user-789"
  }
}
```

## Data Flow

### Agent Configuration Management
```
1. API Request → AgentCreateRequest (DTO)
2. Route → AgentConfigurationService 
3. Service → AgentConfiguration (Entity)
4. Service → AgentConfigurationRepository
5. Repository → Storage (In-Memory/DB)
```

### Chat Completion Flow  
```
1. API Request → ChatCompletionRequest (DTO)
2. Route → Extract session_id from metadata
3. Route → SessionService.get_or_create_session()
4. Route → AgentConfigurationService.get_configuration()
5. Route → AgentFactory.get_or_create_agent()
6. Agent → Execute with conversation history
7. SessionService → Update conversation history
8. Response → ChatCompletionResponse (DTO)
```

## Benefits

### 1. **Maintainability**
- ✅ Clear separation of concerns
- ✅ Single responsibility per layer
- ✅ Easy to locate and modify code

### 2. **Testability**
- ✅ Dependency injection throughout
- ✅ Abstract interfaces for mocking
- ✅ Isolated business logic

### 3. **Scalability**
- ✅ Repository pattern enables different storage backends
- ✅ Service layer can handle complex business logic
- ✅ API layer can support multiple API versions

### 4. **Extensibility**
- ✅ Easy to add new APIs (GraphQL, gRPC)
- ✅ Simple to add new storage implementations
- ✅ Straightforward to extend domain models

## Migration Strategy

### Backward Compatibility
The old `runtime/models.py` file now serves as a compatibility layer:

```python
# Import from new architecture
from runtime.api.models import ChatCompletionRequest
from runtime.domain.entities import AgentConfiguration
# ... etc
```

This ensures existing code continues to work while migrating to the new structure.

### Future Database Integration
The repository pattern makes database integration straightforward:

```python
class DatabaseAgentConfigurationRepository(AgentConfigurationRepository):
    def __init__(self, db_session):
        self.db_session = db_session
    
    def create(self, config: AgentConfiguration) -> AgentConfiguration:
        # SQLAlchemy or other ORM implementation
        pass
```

## File Structure

```
runtime/
├── api/                    # API layer
│   ├── routes/            # Route handlers
│   │   ├── agent_routes.py
│   │   ├── chat_routes.py
│   │   └── health_routes.py
│   └── models/            # API DTOs
│       ├── requests.py
│       └── responses.py
├── services/              # Business logic
│   ├── agent_configuration_service.py
│   └── session_service.py
├── domain/                # Domain layer
│   ├── entities/         # Domain entities
│   │   ├── agent_configuration.py
│   │   └── chat_session.py
│   └── value_objects/    # Value objects
│       ├── chat_message.py
│       └── finish_reason.py
├── repositories/          # Data access
│   ├── agent_configuration_repository.py
│   └── session_repository.py
├── core/                  # Agent runtime
│   ├── template_manager.py
│   ├── agent_factory.py
│   └── scheduler.py
├── infrastructure/        # External dependencies
├── models.py             # Backward compatibility
└── main.py               # Application entry point
```

## Next Steps

1. **Database Integration**: Replace in-memory repositories with database implementations
2. **API Versioning**: Support multiple API versions using the layered structure
3. **Advanced Features**: Add caching, monitoring, and distributed deployment support
4. **Testing**: Comprehensive test coverage for each layer
5. **Documentation**: API documentation and developer guides

This layered architecture provides a solid foundation for building scalable, maintainable agent runtime systems while maintaining OpenAI compatibility and proper separation of concerns.
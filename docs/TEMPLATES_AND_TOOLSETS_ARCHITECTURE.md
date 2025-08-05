# Agent Templates and Toolsets in Layered Architecture

## Overview

Agent templates and toolsets are core extensible concepts that require special consideration in the layered architecture. This document outlines how to properly integrate them while maintaining clean separation of concerns.

## Architecture Placement

### **Agent Templates → Template Layer**

Agent templates deserve their own **Template Layer** because they:
- Are factory/blueprint patterns for creating agents
- Have framework abstraction concerns (LangGraph, LangChain, Custom)
- Require discovery, registration, and lifecycle management
- Are pluggable and extensible by design

### **Toolsets → Toolset Layer + Domain Integration**

Toolsets should span multiple layers because they:
- Have business rules and configuration (Domain Layer)
- Need management services (Service Layer)
- Require external integrations (Infrastructure Layer)
- Are consumed by templates and agents (Cross-cutting)

## Proposed Directory Structure

```
runtime/
├── api/                          # API Layer
│   ├── routes/
│   │   ├── agent_routes.py
│   │   ├── chat_routes.py
│   │   ├── template_routes.py    # NEW: Template management API
│   │   └── toolset_routes.py     # NEW: Toolset management API
│   └── models/
│       ├── requests.py
│       ├── responses.py
│       ├── template_models.py    # NEW: Template DTOs
│       └── toolset_models.py     # NEW: Toolset DTOs
├── services/                     # Service Layer
│   ├── agent_configuration_service.py
│   ├── session_service.py
│   └── toolset_service.py        # MOVED: From runtime/toolset/
├── domain/                       # Domain Layer
│   ├── entities/
│   │   ├── agent_configuration.py
│   │   ├── chat_session.py
│   │   └── toolset.py           # NEW: Toolset entity
│   └── value_objects/
│       ├── chat_message.py
│       ├── template_metadata.py  # NEW: Template metadata VO
│       └── toolset_configuration.py # NEW: Toolset config VO
├── repositories/                 # Repository Layer
│   ├── agent_configuration_repository.py
│   ├── session_repository.py
│   └── toolset_repository.py     # NEW: Toolset data access
├── templates/                    # Template Layer (RENAMED)
│   ├── manager/                  # Template management
│   │   ├── template_manager.py   # MOVED: From core/
│   │   ├── discovery.py          # MOVED: From core/
│   │   └── registry.py
│   ├── base/                     # Base abstractions
│   │   ├── agent_template.py     # MOVED: From template_agent/base.py
│   │   └── template_interface.py
│   ├── implementations/          # Framework-specific templates
│   │   ├── langgraph/
│   │   │   ├── conversation.py
│   │   │   ├── task.py
│   │   │   └── custom.py
│   │   ├── langchain/
│   │   │   └── ...
│   │   └── custom/
│   │       └── ...
│   └── adapters/                 # Framework adapters
│       ├── langgraph_adapter.py
│       ├── langchain_adapter.py
│       └── custom_adapter.py
├── toolsets/                     # Toolset Layer (RENAMED)
│   ├── manager/                  # Toolset management
│   │   ├── toolset_manager.py    # NEW: High-level management
│   │   ├── factory.py            # NEW: Toolset factory
│   │   └── client.py             # MOVED: From toolset/
│   ├── providers/                # Tool providers
│   │   ├── mcp_provider.py       # MCP integration
│   │   ├── local_provider.py     # Local tools
│   │   └── api_provider.py       # API-based tools
│   └── implementations/          # Concrete toolsets
│       ├── web_search/
│       ├── file_operations/
│       ├── code_execution/
│       └── custom/
├── core/                         # Core Runtime Layer
│   ├── agent_factory.py
│   ├── scheduler.py
│   └── execution_engine.py       # NEW: Agent execution
└── infrastructure/               # Infrastructure Layer
    ├── database/
    ├── cache/
    └── external_services/
```

## Template Layer Implementation

### **Template Management**

```python
# runtime/templates/manager/template_manager.py
class TemplateManager:
    """High-level template management orchestrator."""
    
    def __init__(
        self, 
        discovery: TemplateDiscovery,
        registry: TemplateRegistry,
        adapter_factory: TemplateAdapterFactory
    ):
        self.discovery = discovery
        self.registry = registry
        self.adapter_factory = adapter_factory
    
    async def discover_templates(self) -> list[TemplateInfo]:
        """Discover available templates."""
        return await self.discovery.discover()
    
    async def register_template(self, template_info: TemplateInfo) -> bool:
        """Register a template with framework adapter."""
        adapter = self.adapter_factory.create_adapter(template_info.framework)
        validated_template = await adapter.validate_template(template_info)
        return self.registry.register(validated_template)
    
    async def create_agent_instance(
        self, 
        template_id: str, 
        config: AgentConfiguration
    ) -> BaseAgentTemplate:
        """Create agent instance from template."""
        template_info = self.registry.get_template(template_id)
        adapter = self.adapter_factory.create_adapter(template_info.framework)
        return await adapter.create_instance(template_info, config)
```

### **Framework Adapters**

```python
# runtime/templates/adapters/langgraph_adapter.py
class LangGraphTemplateAdapter(TemplateAdapter):
    """Adapter for LangGraph-based templates."""
    
    async def validate_template(self, template_info: TemplateInfo) -> TemplateInfo:
        """Validate LangGraph template structure."""
        # Validate LangGraph-specific requirements
        pass
    
    async def create_instance(
        self, 
        template_info: TemplateInfo, 
        config: AgentConfiguration
    ) -> BaseAgentTemplate:
        """Create LangGraph agent instance."""
        # Instantiate with LangGraph-specific logic
        pass
```

### **Template API Integration**

```python
# runtime/api/routes/template_routes.py
@router.get("/templates")
async def list_templates(
    request: Request,
    _: bool = Depends(runtime_auth)
) -> TemplateListResponse:
    """List all available templates."""
    template_manager = get_template_manager(request)
    templates = await template_manager.discover_templates()
    return TemplateListResponse(templates=templates)

@router.post("/templates/{template_id}/validate")
async def validate_template_config(
    template_id: str,
    config: TemplateConfigRequest,
    request: Request,
    _: bool = Depends(runtime_auth)
) -> ValidationResponse:
    """Validate template configuration."""
    template_manager = get_template_manager(request)
    result = await template_manager.validate_config(template_id, config)
    return ValidationResponse(valid=result.valid, errors=result.errors)
```

## Toolset Layer Implementation

### **Toolset as Domain Entity**

```python
# runtime/domain/entities/toolset.py
class Toolset(BaseModel):
    """Toolset domain entity."""
    
    id: str = Field(..., description="Toolset identifier")
    name: str = Field(..., description="Toolset name")
    description: str = Field(..., description="Toolset description")
    version: str = Field(..., description="Toolset version")
    toolset_type: ToolsetType = Field(..., description="Type of toolset")
    capabilities: list[str] = Field(default_factory=list, description="Toolset capabilities")
    configuration: ToolsetConfiguration = Field(..., description="Toolset configuration")
    status: ToolsetStatus = Field(default=ToolsetStatus.AVAILABLE, description="Toolset status")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def is_available(self) -> bool:
        """Check if toolset is available for use."""
        return self.status == ToolsetStatus.AVAILABLE
    
    def get_tools(self) -> list[str]:
        """Get list of tools provided by this toolset."""
        return self.configuration.tools
```

### **Toolset Service**

```python
# runtime/services/toolset_service.py
class ToolsetService:
    """Service for managing toolsets."""
    
    def __init__(
        self, 
        repository: ToolsetRepository,
        toolset_manager: ToolsetManager
    ):
        self.repository = repository
        self.toolset_manager = toolset_manager
    
    async def discover_toolsets(self) -> list[Toolset]:
        """Discover available toolsets."""
        return await self.toolset_manager.discover()
    
    async def get_toolset_client(self, toolset_names: list[str]) -> ToolsetClient:
        """Get client for specified toolsets."""
        toolsets = []
        for name in toolset_names:
            toolset = await self.repository.get_by_name(name)
            if toolset and toolset.is_available():
                toolsets.append(toolset)
        
        return await self.toolset_manager.create_client(toolsets)
    
    async def register_toolset(self, toolset: Toolset) -> Toolset:
        """Register a new toolset."""
        # Validate toolset
        await self.toolset_manager.validate(toolset)
        
        # Store in repository
        return await self.repository.create(toolset)
```

### **Toolset Manager**

```python
# runtime/toolsets/manager/toolset_manager.py
class ToolsetManager:
    """High-level toolset management orchestrator."""
    
    def __init__(
        self, 
        factory: ToolsetFactory,
        providers: dict[ToolsetType, ToolsetProvider]
    ):
        self.factory = factory
        self.providers = providers
    
    async def discover(self) -> list[Toolset]:
        """Discover toolsets from all providers."""
        toolsets = []
        for provider in self.providers.values():
            discovered = await provider.discover()
            toolsets.extend(discovered)
        return toolsets
    
    async def create_client(self, toolsets: list[Toolset]) -> ToolsetClient:
        """Create unified client for multiple toolsets."""
        clients = []
        for toolset in toolsets:
            provider = self.providers[toolset.toolset_type]
            client = await provider.create_client(toolset)
            clients.append(client)
        
        return CompositeToolsetClient(clients)
```

## Integration with Existing Layers

### **Domain Layer Integration**

```python
# runtime/domain/entities/agent_configuration.py
class AgentConfiguration(BaseModel):
    # ... existing fields ...
    template_id: str = Field(..., description="Template identifier")
    toolset_ids: list[str] = Field(default_factory=list, description="Associated toolset IDs")
    
    def get_template_metadata(self) -> TemplateMetadata:
        """Get template metadata for this configuration."""
        # Reference to template layer
        pass
    
    def get_required_toolsets(self) -> list[str]:
        """Get required toolsets for this agent."""
        return self.toolset_ids
```

### **Service Layer Integration**

```python
# runtime/services/agent_configuration_service.py
class AgentConfigurationService:
    def __init__(
        self, 
        repository: AgentConfigurationRepository,
        template_manager: TemplateManager,  # NEW dependency
        toolset_service: ToolsetService     # NEW dependency
    ):
        self.repository = repository
        self.template_manager = template_manager
        self.toolset_service = toolset_service
    
    async def create_configuration(self, request: AgentCreateRequest) -> AgentConfiguration:
        """Create configuration with template and toolset validation."""
        # Validate template exists
        template = await self.template_manager.get_template(request.template_id)
        if not template:
            raise ValueError(f"Template {request.template_id} not found")
        
        # Validate toolsets exist and are available
        for toolset_id in request.toolset_ids:
            toolset = await self.toolset_service.get_toolset(toolset_id)
            if not toolset or not toolset.is_available():
                raise ValueError(f"Toolset {toolset_id} not available")
        
        # Create configuration
        config = AgentConfiguration(...)
        return await self.repository.create(config)
```

### **Runtime Integration**

```python
# runtime/main.py
class AgentRuntime:
    def __init__(self):
        # Template layer
        self.template_discovery = TemplateDiscovery()
        self.template_registry = TemplateRegistry()
        self.template_adapter_factory = TemplateAdapterFactory()
        self.template_manager = TemplateManager(
            self.template_discovery,
            self.template_registry,
            self.template_adapter_factory
        )
        
        # Toolset layer  
        self.toolset_providers = {
            ToolsetType.MCP: MCPToolsetProvider(),
            ToolsetType.CUSTOM: CustomToolsetProvider(),
        }
        self.toolset_factory = ToolsetFactory()
        self.toolset_manager = ToolsetManager(
            self.toolset_factory,
            self.toolset_providers
        )
        
        # Repositories
        self.toolset_repository = InMemoryToolsetRepository()
        
        # Services (with new dependencies)
        self.toolset_service = ToolsetService(
            self.toolset_repository,
            self.toolset_manager
        )
        self.agent_service = AgentConfigurationService(
            self.config_repository,
            self.template_manager,      # NEW
            self.toolset_service        # NEW
        )
        
        # Core runtime (with template integration)
        self.agent_factory = AgentFactory(
            self.template_manager,      # Updated dependency
            self.toolset_service
        )
```

## Benefits of This Architecture

### **1. Clear Separation of Concerns**
- **Templates**: Framework abstraction and agent creation
- **Toolsets**: Tool management and external integrations
- **Domain**: Business rules and entity relationships
- **Services**: Orchestration and business logic

### **2. Extensibility**
- New template frameworks can be added via adapters
- New toolset providers can be plugged in
- Templates and toolsets are discoverable and registrable

### **3. Testability**
- Each layer can be tested independently
- Template adapters can be mocked
- Toolset providers can be stubbed

### **4. Maintainability**
- Framework-specific code is isolated
- Business logic is separate from infrastructure
- Clear dependencies between layers

## Migration Strategy

1. **Phase 1**: Move template code to new structure
2. **Phase 2**: Implement toolset domain entities and services
3. **Phase 3**: Add template and toolset APIs
4. **Phase 4**: Update agent factory integration
5. **Phase 5**: Add advanced features (hot-reload, validation)

This architecture properly places templates and toolsets while maintaining the clean layered structure and enabling future extensibility.
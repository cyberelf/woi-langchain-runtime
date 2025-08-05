# Templates and Toolsets Layered Architecture Refactoring Plan

## Overview

This plan outlines the step-by-step migration of agent templates and toolsets into the proper layered architecture. The refactoring will be done incrementally to maintain system stability.

## Phase 1: Foundation Setup (2-3 hours)

### Step 1.1: Create New Directory Structure
**Goal**: Set up the directory structure for templates and toolsets layers

**Tasks**:
- [ ] Create `runtime/templates/` directory structure
- [ ] Create `runtime/toolsets/` directory structure  
- [ ] Create domain entities for toolsets
- [ ] Create value objects for template metadata

**Files to Create**:
```
runtime/
├── templates/
│   ├── __init__.py
│   ├── manager/
│   │   └── __init__.py
│   ├── base/
│   │   └── __init__.py
│   ├── implementations/
│   │   └── __init__.py
│   └── adapters/
│       └── __init__.py
├── toolsets/
│   ├── __init__.py
│   ├── manager/
│   │   └── __init__.py
│   ├── providers/
│   │   └── __init__.py
│   └── implementations/
│       └── __init__.py
└── domain/
    ├── entities/
    │   └── toolset.py
    └── value_objects/
        ├── template_metadata.py
        └── toolset_configuration.py
```

### Step 1.2: Create Toolset Domain Models
**Goal**: Define toolset as proper domain entities

**Tasks**:
- [ ] Create `Toolset` entity in domain layer
- [ ] Create `ToolsetConfiguration` value object
- [ ] Create `ToolsetStatus` enum
- [ ] Add toolset repository interface

### Step 1.3: Update Agent Configuration Entity
**Goal**: Add proper relationships to templates and toolsets

**Tasks**:
- [ ] Add `template_metadata` property to `AgentConfiguration`
- [ ] Add `toolset_ids` list to `AgentConfiguration`
- [ ] Add validation methods for template/toolset relationships

## Phase 2: Template Layer Migration (3-4 hours)

### Step 2.1: Move Template Management
**Goal**: Migrate template manager to templates layer

**Tasks**:
- [ ] Move `runtime/core/template_manager.py` → `runtime/templates/manager/template_manager.py`
- [ ] Move `runtime/core/discovery.py` → `runtime/templates/manager/discovery.py`
- [ ] Create `runtime/templates/manager/registry.py`
- [ ] Update imports throughout codebase

### Step 2.2: Move Base Template Classes
**Goal**: Migrate base template abstractions

**Tasks**:
- [ ] Move `runtime/template_agent/base.py` → `runtime/templates/base/agent_template.py`
- [ ] Create `runtime/templates/base/template_interface.py`
- [ ] Update base classes to use new domain models
- [ ] Fix imports in existing template implementations

### Step 2.3: Move Template Implementations
**Goal**: Migrate concrete template implementations

**Tasks**:
- [ ] Move `runtime/template_agent/langgraph/` → `runtime/templates/implementations/langgraph/`
- [ ] Update template implementations to use new base classes
- [ ] Create placeholder directories for other frameworks
- [ ] Update template registration logic

### Step 2.4: Create Template Adapters
**Goal**: Implement framework adaptation layer

**Tasks**:
- [ ] Create `runtime/templates/adapters/base_adapter.py`
- [ ] Create `runtime/templates/adapters/langgraph_adapter.py`
- [ ] Create `runtime/templates/adapters/adapter_factory.py`
- [ ] Integrate adapters with template manager

## Phase 3: Toolset Layer Migration (3-4 hours)

### Step 3.1: Create Toolset Repository
**Goal**: Implement data access layer for toolsets

**Tasks**:
- [ ] Create `runtime/repositories/toolset_repository.py`
- [ ] Create `InMemoryToolsetRepository` implementation
- [ ] Add CRUD operations for toolsets
- [ ] Create repository interface

### Step 3.2: Migrate Toolset Service
**Goal**: Move toolset service to proper service layer

**Tasks**:
- [ ] Move `runtime/toolset/toolset_service.py` → `runtime/services/toolset_service.py`
- [ ] Update service to use toolset repository
- [ ] Update service to work with toolset entities
- [ ] Add business logic for toolset validation

### Step 3.3: Create Toolset Manager
**Goal**: Implement high-level toolset orchestration

**Tasks**:
- [ ] Create `runtime/toolsets/manager/toolset_manager.py`
- [ ] Create `runtime/toolsets/manager/factory.py`
- [ ] Implement toolset discovery logic
- [ ] Add toolset client creation logic

### Step 3.4: Move Toolset Providers
**Goal**: Migrate toolset implementations to providers

**Tasks**:
- [ ] Move `runtime/toolset/langgraph/` → `runtime/toolsets/providers/langgraph/`
- [ ] Create `runtime/toolsets/providers/mcp_provider.py`
- [ ] Create `runtime/toolsets/providers/local_provider.py`
- [ ] Update providers to use new toolset entities

## Phase 4: API Layer Integration (2-3 hours)

### Step 4.1: Create Template API
**Goal**: Add template management endpoints

**Tasks**:
- [ ] Create `runtime/api/routes/template_routes.py`
- [ ] Create `runtime/api/models/template_models.py`
- [ ] Add endpoints for template discovery and validation
- [ ] Integrate with template manager

### Step 4.2: Create Toolset API
**Goal**: Add toolset management endpoints

**Tasks**:
- [ ] Create `runtime/api/routes/toolset_routes.py`
- [ ] Create `runtime/api/models/toolset_models.py`
- [ ] Add endpoints for toolset listing and configuration
- [ ] Integrate with toolset service

### Step 4.3: Update Existing APIs
**Goal**: Update agent and chat APIs to use new layers

**Tasks**:
- [ ] Update agent routes to validate templates and toolsets
- [ ] Update chat routes to use template manager
- [ ] Add template and toolset information to responses
- [ ] Update error handling

## Phase 5: Runtime Integration (2-3 hours)

### Step 5.1: Update Agent Factory
**Goal**: Integrate agent factory with new layers

**Tasks**:
- [ ] Update `AgentFactory` to use `TemplateManager`
- [ ] Update `AgentFactory` to use `ToolsetService`
- [ ] Implement auto-instantiation from configurations
- [ ] Add template validation during agent creation

### Step 5.2: Update Runtime Initialization
**Goal**: Initialize new layers in main runtime

**Tasks**:
- [ ] Update `runtime/main.py` to create template manager
- [ ] Update `runtime/main.py` to create toolset manager
- [ ] Add dependency injection for new services
- [ ] Update app state injection

### Step 5.3: Update Service Dependencies
**Goal**: Wire up cross-layer dependencies

**Tasks**:
- [ ] Update `AgentConfigurationService` with template/toolset dependencies
- [ ] Update service initialization order
- [ ] Add proper error handling for missing dependencies
- [ ] Test integration between layers

## Phase 6: Testing and Documentation (2-3 hours)

### Step 6.1: Create Tests
**Goal**: Ensure new architecture works correctly

**Tasks**:
- [ ] Create unit tests for template layer
- [ ] Create unit tests for toolset layer
- [ ] Create integration tests for API endpoints
- [ ] Test backward compatibility

### Step 6.2: Update Documentation
**Goal**: Document the new architecture

**Tasks**:
- [ ] Update architecture documentation
- [ ] Create template development guide
- [ ] Create toolset development guide
- [ ] Update API documentation

### Step 6.3: Clean Up Legacy Code
**Goal**: Remove old code and update imports

**Tasks**:
- [ ] Remove old template_agent directory
- [ ] Remove old toolset directory
- [ ] Update all imports throughout codebase
- [ ] Clean up unused code

## Phase 7: Advanced Features (Optional - 2-3 hours)

### Step 7.1: Template Hot-Reload
**Goal**: Enable dynamic template loading

**Tasks**:
- [ ] Add file watching for template changes
- [ ] Implement template reload mechanism
- [ ] Add hot-reload API endpoints

### Step 7.2: Toolset Registry
**Goal**: Enable dynamic toolset registration

**Tasks**:
- [ ] Create persistent toolset registry
- [ ] Add toolset installation endpoints
- [ ] Implement toolset versioning

## Execution Strategy

### Order of Execution
1. **Phase 1**: Foundation (mandatory)
2. **Phase 2**: Templates (mandatory)
3. **Phase 3**: Toolsets (mandatory)
4. **Phase 4**: API Integration (mandatory)
5. **Phase 5**: Runtime Integration (mandatory)
6. **Phase 6**: Testing & Documentation (mandatory)
7. **Phase 7**: Advanced Features (optional)

### Risk Mitigation
- Create feature branches for each phase
- Maintain backward compatibility during migration
- Test each phase thoroughly before proceeding
- Keep rollback plans for each phase

### Dependencies
- Phase 2 depends on Phase 1
- Phase 3 depends on Phase 1
- Phase 4 depends on Phases 2 & 3
- Phase 5 depends on Phases 2, 3 & 4
- Phase 6 depends on Phase 5

### Estimated Timeline
- **Total**: 14-20 hours
- **Minimum Viable**: 12 hours (Phases 1-6)
- **Full Implementation**: 20 hours (all phases)

### Success Criteria
- [ ] All existing functionality preserved
- [ ] New template layer operational
- [ ] New toolset layer operational
- [ ] APIs working with new architecture
- [ ] Agent creation using new layers
- [ ] Comprehensive test coverage
- [ ] Updated documentation

## Next Steps

1. **Start with Phase 1.1**: Create directory structure
2. **Implement incrementally**: One step at a time
3. **Test continuously**: Verify each step works
4. **Update documentation**: Keep docs current

Ready to begin implementation! 🚀
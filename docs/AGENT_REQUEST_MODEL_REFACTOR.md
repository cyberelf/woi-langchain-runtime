# Design for Refactoring CreateAgentRequest Model

## 1. Introduction

The current `CreateAgentRequest` model in `runtime/infrastructure/web/models/requests.py` has become a large and complex data structure responsible for handling multiple concerns. It mixes fields related to agent identity, template selection, and configuration, which makes the code harder to understand, maintain, and extend. This document proposes a refactoring of the `CreateAgentRequest` to improve its structure and align it with the principles of Domain-Driven Design (DDD) by separating these concerns into distinct, more focused models.

## 2. Problem Statement

The `CreateAgentRequest` model currently includes fields for:
-   **Agent Identity**: `id`, `name`, `description`, `avatar_url`, etc. These are used for the agent's "card" or profile.
-   **Template Selection**: `template_id`, `template_version`, etc. These are used to find and instantiate a specific agent template.
-   **Configuration**: `config`, `configuration`, `system_prompt`, etc. These are used to customize the agent's behavior.

This mix of responsibilities in a single model leads to a monolithic structure that is not aligned with the different contexts in which these pieces of data are used.

## 3. Proposed Solution

**Important Note**: The external API interface must remain unchanged to maintain backward compatibility. The refactoring will be purely internal - the `CreateAgentRequest` will continue to accept the current flat structure, but will internally parse the data into smaller, more cohesive Pydantic models. Each internal model will represent a specific concern.

### 3.1. New Internal Models

The following internal models will be created to represent the different aspects of an agent creation request.

#### 3.1.1. `AgentIdentityModel`

This model will contain the core attributes that define the agent's identity.

```python
from pydantic import BaseModel, Field
from typing import Optional

class AgentIdentityModel(BaseModel):
    """Model for core agent identity attributes."""
    id: str = Field(..., description="Agent line ID (logical identifier)")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    avatar_url: Optional[str] = Field(None, description="Agent avatar URL")
    type: str = Field(..., description="Agent type")
    owner_id: str = Field(..., description="Agent owner ID for beta access control")
    status: Optional[str] = Field("draft", description="Agent status: draft, submitted, pending, published, revoked (default: draft)")
    agent_line_id: str = Field(..., description="Agent line ID")
    version_type: Optional[str] = Field("beta", description="Version type: beta or release (default: beta)")
    version_number: Optional[str] = Field("v1", description="Version number: 'v1', 'v2', etc. (default: v1)")
```

#### 3.1.2. `AgentTemplateModel`

This model will encapsulate the information required to select and version the agent template.

```python
class AgentTemplateModel(BaseModel):
    """Model for agent template selection."""
    template_id: str = Field(..., description="Template type identifier")
    template_version: Optional[str] = Field(None, description="The version of the template to use.")
    template_version_id: str = Field(..., description="Template version string")

    def get_template_version(self) -> Optional[str]:
        """Get template version, preferring template_version_id over template_version."""
        return self.template_version_id or self.template_version
```

#### 3.1.3. `AgentConfigurationModel`

This model will hold all the configuration-related fields that customize the agent's behavior.

```python
class AgentConfigurationModel(BaseModel):
    """Model for agent configuration."""
    template_config: Optional[dict] = Field(None, description="Template configuration")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    conversation_config: Optional[dict] = Field(None, description="Conversation configuration")
    toolsets: Optional[list[str]] = Field(None, description="Available toolsets")
    llm_config_id: Optional[str] = Field(None, description="LLM configuration ID")

    def get_configuration(self) -> dict:
        """Get configuration from template_config."""
        config = {}
        if self.template_config:
            # Handle nested conversation config with camelCase conversion
            template_config = self.template_config.copy()
            if "conversation" in template_config:
                conv_config = template_config["conversation"]
                if "historyLength" in conv_config:
                    conv_config["history_length"] = conv_config.pop("historyLength")
                template_config.update(conv_config)
                template_config.pop("conversation")
            config.update(template_config)
        return config
```

### 3.2. Refactored `CreateAgentRequest`

The `CreateAgentRequest` model will maintain its current flat structure for external compatibility, but will internally parse the data into the new structured models.

```python
class CreateAgentRequest(BaseModel):
    """HTTP request model for creating agents.
    
    Infrastructure layer model that handles HTTP/JSON serialization.
    Maps to domain command objects.
    """
    
    # Core fields - following API specification
    id: str = Field(..., description="Agent line ID (logical identifier)")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    avatar_url: Optional[str] = Field(None, description="Agent avatar URL")
    type: str = Field(..., description="Agent type")
    
    # Template fields - following API specification
    template_id: str = Field(..., description="Template type identifier")
    template_version: Optional[str] = Field(None, description="The version of the template to use.")
    template_version_id: str = Field(..., description="Template version string")
    
    # Configuration fields
    system_prompt: Optional[str] = Field(None, description="System prompt")
    conversation_config: Optional[dict] = Field(None, description="Conversation configuration")
    toolsets: Optional[list[str]] = Field(None, description="Available toolsets")
    llm_config_id: Optional[str] = Field(None, description="LLM configuration ID")
    template_config: Optional[dict] = Field(None, description="Template configuration")

    # Metadata - following API specification
    agent_line_id: str = Field(..., description="Agent line ID")
    version_type: Optional[str] = Field("beta", description="Version type: beta or release (default: beta)")
    version_number: Optional[str] = Field("v1", description="Version number: 'v1', 'v2', etc. (default: v1)")
    owner_id: str = Field(..., description="Agent owner ID for beta access control")
    status: Optional[str] = Field("draft", description="Agent status: draft, submitted, pending, published, revoked (default: draft)")

    model_config = ConfigDict(extra="forbid")

    def get_identity(self) -> AgentIdentityModel:
        """Parse identity-related fields into AgentIdentityModel."""
        return AgentIdentityModel(
            id=self.id,
            name=self.name,
            description=self.description,
            avatar_url=self.avatar_url,
            type=self.type,
            owner_id=self.owner_id,
            status=self.status,
            agent_line_id=self.agent_line_id,
            version_type=self.version_type,
            version_number=self.version_number
        )

    def get_template(self) -> AgentTemplateModel:
        """Parse template-related fields into AgentTemplateModel."""
        return AgentTemplateModel(
            template_id=self.template_id,
            template_version=self.template_version,
            template_version_id=self.template_version_id
        )

    def get_agent_configuration(self) -> AgentConfigurationModel:
        """Parse configuration-related fields into AgentConfigurationModel."""
        return AgentConfigurationModel(
            template_config=self.template_config,
            system_prompt=self.system_prompt,
            conversation_config=self.conversation_config,
            toolsets=self.toolsets,
            llm_config_id=self.llm_config_id
        )

    def get_template_version(self) -> Optional[str]:
        """Get template version, preferring template_version_id over template_version."""
        return self.get_template().get_template_version()

    def get_configuration(self) -> dict:
        """Get configuration from template_config."""
        return self.get_agent_configuration().get_configuration()

    def get_metadata(self) -> dict:
        """Get metadata with additional fields."""
        identity = self.get_identity()
        config = self.get_agent_configuration()
        
        meta = identity.metadata or {}
        if identity.description:
            meta["description"] = identity.description
        if identity.type:
            meta["type"] = identity.type
        if config.system_prompt:
            meta["system_prompt"] = config.system_prompt
        if config.llm_config_id:
            meta["llm_config_id"] = config.llm_config_id
        return meta
```

## 4. Field Mapping

| Old `CreateAgentRequest` Field | New Model                 | New Field Name   |
| ------------------------------ | ------------------------- | ---------------- |
| `id`                           | `AgentIdentityModel`      | `id`             |
| `name`                         | `AgentIdentityModel`      | `name`           |
| `description`                  | `AgentIdentityModel`      | `description`    |
| `avatar_url`                   | `AgentIdentityModel`      | `avatar_url`     |
| `type`                         | `AgentIdentityModel`      | `type`           |
| `owner_id`                     | `AgentIdentityModel`      | `owner_id`       |
| `status`                       | `AgentIdentityModel`      | `status`         |
| `agent_line_id`                | `AgentIdentityModel`      | `agent_line_id`  |
| `version_type`                 | `AgentIdentityModel`      | `version_type`   |
| `version_number`               | `AgentIdentityModel`      | `version_number` |
| `template_id`                  | `AgentTemplateModel`      | `template_id`    |
| `template_version`             | `AgentTemplateModel`      | `template_version` |
| `template_version_id`          | `AgentTemplateModel`      | `template_version_id` |
| `template_config`              | `AgentConfigurationModel` | `template_config` |
| `system_prompt`                | `AgentConfigurationModel` | `system_prompt`  |
| `conversation_config`          | `AgentConfigurationModel` | `conversation_config` |
| `toolsets`                     | `AgentConfigurationModel` | `toolsets`       |
| `llm_config_id`                | `AgentConfigurationModel` | `llm_config_id`  |

## 5. Benefits

-   **Separation of Concerns**: Each model has a single, well-defined responsibility.
-   **Improved Readability**: The code becomes easier to understand as the data structures are more aligned with their purpose.
-   **Enhanced Maintainability**: Changes to one area (e.g., template selection) will not affect the models for other areas (e.g., agent identity).
-   **Clearer API**: The new structure can be reflected in the API documentation, making it easier for API consumers to understand the request structure.

## 6. Code Analysis and Implementation Plan

Before proceeding with the implementation, we need to identify all parts of the codebase that use `CreateAgentRequest` and understand the impact.

### 6.1. Code Analysis Results

Based on analysis of the codebase, the following files use `CreateAgentRequest`:

#### Core Infrastructure Files:
1. **`runtime/infrastructure/web/models/requests.py`** - Primary model definition
2. **`runtime/infrastructure/web/routes/agent_routes.py`** - API route handler that uses the request

#### Template and Execution Files:
3. **`runtime/templates/base.py`** - Base agent template initialization
4. **`runtime/infrastructure/frameworks/langgraph/templates/base.py`** - LangGraph base template
5. **`runtime/infrastructure/frameworks/langgraph/templates/simple.py`** - Simple LangGraph template
6. **`runtime/infrastructure/frameworks/langgraph/templates/conversation.py`** - Conversation template
7. **`runtime/infrastructure/frameworks/langgraph/executor.py`** - LangGraph executor

#### Task Management:
8. **`runtime/core/agent_task_manager.py`** - Task management system

#### Client and Examples:
9. **`client_sdk/__init__.py`** - Client SDK
10. **`client_sdk/client.py`** - Client implementation
11. **`cli_tool.py`** - CLI tool
12. **`examples/simple_agent_cli.py`** - Example CLI

#### Test Coverage:
- **No test files** currently use `CreateAgentRequest` directly

### 6.2. Current Usage Analysis

#### High-Impact Files (require updates):

**`runtime/infrastructure/web/routes/agent_routes.py`:**
- Current usage: `request.name`, `request.template_id`, `request.get_configuration()`, `request.get_template_version()`, `request.get_metadata()`, `request.id`
- Change required: Update to use parsed models for better separation of concerns

**`runtime/templates/base.py`:**
- Current usage: `agent_data.id`, `agent_data.name`, `agent_data.template_id`, `agent_data.template_version`, `agent_data.config`
- Change required: Update to use parsed models instead of direct field access

**Template files (LangGraph templates):**
- Similar usage pattern to base template
- Will benefit from structured access to configuration vs identity fields

#### Medium-Impact Files (may benefit from updates):

**`runtime/core/agent_task_manager.py`:**
- Imports `CreateAgentRequest` but usage needs to be examined more closely

#### Low-Impact Files (minimal/no changes needed):

**Client SDK and Examples:**
- These create `CreateAgentRequest` instances but don't process them
- No changes needed as they construct the request objects

### 6.3. Implementation Steps

1. **Add Internal Models**: Add the three new internal models (`AgentIdentityModel`, `AgentTemplateModel`, `AgentConfigurationModel`) to the requests.py file

2. **Update CreateAgentRequest**: Add the parsing methods (`get_identity()`, `get_template()`, `get_agent_configuration()`) to the existing model

3. **Update High-Impact Files**:
   - Update `agent_routes.py` to use parsed models
   - Update `runtime/templates/base.py` to use structured access
   - Update LangGraph template files

4. **Test Backward Compatibility**: Ensure all existing functionality continues to work

5. **Add Unit Tests**: Add tests for the new parsing functionality

6. **Update Documentation**: Update any internal documentation that references the structure

### 6.4. Backward Compatibility

**Important**: The external API interface will remain completely unchanged. This is purely an internal refactoring that:
- Maintains the same JSON request structure
- Keeps all existing field names and types
- Preserves all existing validation rules
- Does not break any existing API clients

### 6.5. Impact Assessment

**Minimal Impact**: Since the external interface remains unchanged:
- **API Clients**: No changes required
- **Route Handlers**: May need minor updates to use new parsing methods
- **Application Services**: May need updates to work with parsed models instead of flat structure
- **Tests**: Existing tests should continue to work; new tests may be added for internal structure

This approach ensures that the refactoring improves internal code organization without breaking existing integrations.

## 7. Next Steps

With the analysis complete, the implementation can proceed as follows:

1. **Phase 1**: Implement the internal models in `requests.py`
2. **Phase 2**: Update high-impact consumer files
3. **Phase 3**: Add comprehensive tests
4. **Phase 4**: Validate backward compatibility

The refactoring is designed to be incremental and non-breaking, allowing for safe deployment without service interruption.

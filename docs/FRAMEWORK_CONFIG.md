# Framework Configuration Validation

## 🎯 Overview

This document describes the pydantic-based configuration validation system implemented for the LangGraph framework. The system ensures type safety and validation during framework executor initialization.

## 📁 Structure

```
runtime/infrastructure/frameworks/langgraph/
├── config.py              # Pydantic configuration models
├── executor.py             # Framework executor with validation
├── llm/service.py          # LLM service using validated config
└── toolsets/service.py     # Toolset service using validated config
```

## 🏗️ Configuration Models

### 1. LLM Configuration Models

#### `LLMProviderConfig`
```python
class LLMProviderConfig(BaseModel):
    type: Literal["openai", "anthropic", "deepseek", "google", "test"]
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = Field(0.7, ge=0.0, le=2.0)  # Validated range
    max_tokens: int = Field(1000, gt=0)              # Must be positive
    metadata: dict[str, Any] = Field(default_factory=dict)
```

#### `LLMConfig`
```python
class LLMConfig(BaseModel):
    providers: dict[str, LLMProviderConfig] = Field(default_factory=dict)
    default_provider: str = Field("test")
    fallback_provider: Optional[str] = None
    
    def get_provider_config(self, provider_name: str) -> LLMProviderConfig:
        # Returns validated provider configuration
```

### 2. Toolset Configuration Models

#### `ToolsetServerConfig`
```python
class ToolsetServerConfig(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
```

#### `ToolsetConfig`
```python
class ToolsetConfig(BaseModel):
    type: Literal["mcp", "custom"]
    config: dict[str, Any] = Field(default_factory=dict)
    
    @validator("config")
    def validate_config_by_type(cls, v, values):
        # Type-specific validation logic
```

#### `ToolsetsConfig`
```python
class ToolsetsConfig(BaseModel):
    toolsets: dict[str, ToolsetConfig] = Field(default_factory=dict)
    default_toolsets: list[str] = Field(default_factory=list)
    
    def get_toolset_config(self, name: str) -> Optional[ToolsetConfig]:
        # Returns validated toolset configuration
```

### 3. Framework Configuration

#### `LangGraphFrameworkConfig`
```python
class LangGraphFrameworkConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    toolsets: ToolsetsConfig = Field(default_factory=ToolsetsConfig)
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "LangGraphFrameworkConfig":
        # Validates and creates configuration from dictionary
    
    @classmethod
    def create_default(cls) -> "LangGraphFrameworkConfig":
        # Creates safe default configuration
```

## 🔧 Framework Executor Integration

### Initialization with Validation

```python
class LangGraphFrameworkExecutor(FrameworkExecutor):
    def __init__(self, service_config=None):
        super().__init__()
        self._framework_config = None
        self._initialize_configuration(service_config)
    
    def _initialize_configuration(self, service_config):
        """Initialize and validate framework configuration."""
        try:
            # Get configuration data from service config or global config
            config_data = self._get_config_data(service_config)
            
            # Validate using pydantic models
            self._framework_config = LangGraphFrameworkConfig.from_dict(config_data)
            logger.info("LangGraph framework configuration validated successfully")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            # Fall back to safe defaults
            self._framework_config = LangGraphFrameworkConfig.create_default()
```

### Service Integration

```python
def get_llm_service(self) -> Any:
    """Get LLM service with validated configuration."""
    if self._llm_service is None:
        # Use validated configuration
        llm_config = self._framework_config.llm.dict()
        self._llm_service = LangGraphLLMService(llm_config)
    return self._llm_service

def get_toolset_service(self) -> Any:
    """Get toolset service with validated configuration."""
    if self._toolset_service is None:
        # Use validated configuration
        toolsets_config = self._framework_config.toolsets
        toolset_config = {name: config.dict() for name, config in toolsets_config.toolsets.items()}
        self._toolset_service = LangGraphToolsetService(toolset_config)
    return self._toolset_service
```

## 📊 Configuration Flow

```
Environment Variables
        ↓
ServiceConfig (pydantic-settings)
        ↓
LangGraphFrameworkConfig (pydantic validation)
        ↓
LLMService & ToolsetService (validated dictionaries)
```

## ✨ Validation Features

### 1. **Type Safety**
- All configuration fields are strongly typed
- Automatic type conversion where appropriate
- Clear type errors for invalid data

### 2. **Field Validation**
- Temperature: Must be between 0.0 and 2.0
- Max tokens: Must be positive integer
- Required fields: Enforced by pydantic

### 3. **Custom Validators**
- LLM provider validation (valid provider types)
- Toolset type-specific configuration validation
- MCP server configuration validation

### 4. **Error Handling**
- Clear validation error messages
- Graceful fallback to default configurations
- Detailed logging of validation failures

## 🎯 Usage Examples

### Valid Configuration
```json
{
  "llm": {
    "providers": {
      "openai": {
        "type": "openai",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
        "api_key": "${OPENAI_API_KEY}"
      },
      "test": {
        "type": "test",
        "model": "test-model",
        "temperature": 0.1,
        "max_tokens": 500
      }
    },
    "default_provider": "test"
  },
  "toolsets": {
    "toolsets": {
      "web_search": {
        "type": "mcp",
        "config": {
          "servers": [
            {
              "name": "search_server",
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-web-search"]
            }
          ],
          "timeout": 30
        }
      }
    }
  }
}
```

### Environment Variable Configuration
```bash
export SERVICES_CONFIG='{"llm": {"providers": {"test": {"type": "test", "model": "test-model"}}}}'
```

## 🚨 Validation Examples

### Invalid Temperature (Rejected)
```json
{
  "llm": {
    "providers": {
      "invalid": {
        "type": "openai",
        "model": "gpt-4",
        "temperature": 5.0  // ❌ Error: must be <= 2.0
      }
    }
  }
}
```

### Invalid Max Tokens (Rejected)
```json
{
  "llm": {
    "providers": {
      "invalid": {
        "type": "openai",
        "model": "gpt-4",
        "max_tokens": -100  // ❌ Error: must be > 0
      }
    }
  }
}
```

## ✅ Benefits

### 1. **Early Validation**
- Configuration errors caught during framework initialization
- No runtime failures due to invalid configurations
- Clear error messages for debugging

### 2. **Type Safety**
- Compile-time type checking with mypy
- Runtime type validation with pydantic
- Prevents configuration-related bugs

### 3. **Default Fallbacks**
- Safe default configurations when validation fails
- Framework can always initialize successfully
- Graceful degradation for production environments

### 4. **Developer Experience**
- Clear configuration schema documentation
- IDE autocomplete for configuration fields
- Validation error messages point to specific issues

### 5. **Extensibility**
- Easy to add new configuration fields
- Custom validators for complex validation logic
- Framework-specific configuration without affecting other frameworks

## 🔄 Migration from Dict-Based Config

### Before
```python
# Raw dictionary configuration
toolset_config = {"web_search": {"type": "mcp", "timeout": 30}}
service = LangGraphToolsetService(toolset_config)
```

### After  
```python
# Validated pydantic configuration
config_data = {"toolsets": {"toolsets": {"web_search": {"type": "mcp", "config": {"timeout": 30}}}}}
framework_config = LangGraphFrameworkConfig.from_dict(config_data)
service = LangGraphToolsetService(framework_config.toolsets.toolsets)
```

## 🎯 Summary

The framework configuration validation system provides:

1. **🛡️ Type Safety**: Pydantic models with strong typing
2. **✅ Validation**: Field constraints and custom validators  
3. **🔄 Integration**: Seamless integration with framework executor
4. **📋 Defaults**: Safe fallback configurations
5. **🧹 Clean Code**: Minimal changes to existing services
6. **🚀 Production Ready**: Robust error handling and logging

This approach ensures configuration reliability while maintaining the simplicity achieved by using third-party libraries instead of custom configuration management code.

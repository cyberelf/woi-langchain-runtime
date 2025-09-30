# Agent Runtime Configuration Guide

This directory contains example configuration files for the LangChain Agent Runtime system with comprehensive LLM and toolset configurations.

## 📁 Files Overview

### Configuration Files
- **`example.env`** - Complete environment variables template
- **`services-config.json`** - Full-featured services configuration with multiple LLM providers and toolsets
- **`simple-config.json`** - Minimal configuration for quick setup
- **`README.md`** - This guide

### Helper Scripts  
- **`validate-config.py`** - Validate your configuration files
- **`show-templates.py`** - Show available agent templates and their schemas

## 🚀 Quick Start

### 1. Environment Setup

Copy the example environment file and customize it:

```bash
cp config/example.env .env
```

Edit `.env` and add your API keys:
```bash
# Required: At least one LLM provider
OPENAI_API_KEY=sk-your-actual-openai-key-here
# Optional: Additional providers
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key-here
DEEPSEEK_API_KEY=sk-your-actual-deepseek-key-here
```

### 2. Choose Your Configuration

#### Option A: Simple Configuration (Recommended for beginners)
```bash
# In your .env file
SERVICES_CONFIG_FILE=config/simple-config.json
```

#### Option B: Full Configuration (Production-ready)
```bash
# In your .env file  
SERVICES_CONFIG_FILE=config/services-config.json
```

#### Option C: Inline JSON Configuration (Not Recommended)
```bash
# In your .env file - only use for very simple configs
SERVICES_CONFIG='{"llm":{"providers":{"openai":{"type":"openai","model":"gpt-4o-mini","api_key":"${OPENAI_API_KEY}","temperature":0.7,"max_tokens":2000}},"default_provider":"openai"}}'
```

> ⚠️  **Note**: If both `SERVICES_CONFIG_FILE` and `SERVICES_CONFIG` are set, the file takes priority.

### 3. Validate Your Configuration (Optional)

```bash
# Validate your configuration
python config/validate-config.py config/services-config.json

# Show available agent templates
python config/show-templates.py
```

### 4. Start the Runtime

```bash
python -m uvicorn runtime.infrastructure.web.main:app --reload
```

## 🤖 LLM Providers Configuration

### Supported Providers

| Provider | Type | Models | Features |
|----------|------|--------|----------|
| OpenAI | `openai` | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | Function calling, vision |
| Anthropic | `anthropic` | claude-3-5-sonnet, claude-3-haiku | Large context, reasoning |
| DeepSeek | `deepseek` | deepseek-coder | Code specialization |
| Google AI | `google` | gemini-1.5-pro | Multimodal, long context |
| Local/Ollama | `openai` | llama3.1, codellama | Privacy, no cost |

### LLM Provider Configuration Format

```json
{
  "providers": {
    "provider-name": {
      "type": "openai|anthropic|deepseek|google",
      "model": "model-name",
      "api_key": "${ENV_VAR_NAME}",
      "base_url": "optional-custom-endpoint",
      "temperature": 0.7,
      "max_tokens": 4000,
      "metadata": {
        "description": "Provider description",
        "cost_per_1k_tokens": 0.01
      }
    }
  },
  "default_provider": "provider-name",
  "fallback_provider": "fallback-provider-name"
}
```

## 🛠️ Toolsets Configuration

### MCP (Model Context Protocol) Toolsets

These are external server processes that provide tools to agents:

```json
{
  "toolset-name": {
    "type": "mcp",
    "config": {
      "servers": [
        {
          "name": "server-name",
          "command": "npx",
          "args": ["@modelcontextprotocol/server-package"],
          "env": {
            "ENV_VAR": "value"
          }
        }
      ],
      "timeout": 30
    }
  }
}
```

### Custom Toolsets

Custom Python tools loaded from a directory:

```json
{
  "toolset-name": {
    "type": "custom",
    "config": {
      "tools_directory": "./tools/custom",
      "auto_discovery": true,
      "timeout": 30,
      "allowed_modules": ["module1", "module2"],
      "environment": {
        "API_KEY": "${API_KEY}"
      }
    }
  }
}
```

### Available MCP Servers

| Server | Package | Capabilities |
|--------|---------|--------------|
| Web Browsing | `@modelcontextprotocol/server-puppeteer` | Browse web, extract text, screenshots |
| Filesystem | `@modelcontextprotocol/server-filesystem` | File operations within workspace |
| SQLite | `@modelcontextprotocol/server-sqlite` | Database queries and operations |
| Git | `@modelcontextprotocol/server-git` | Version control operations |
| HTTP API | `@modelcontextprotocol/server-fetch` | REST API requests |

## 🎯 Agent Templates

**Agent templates are automatically discovered from code, not configured in JSON files.**

### Available Templates

The runtime automatically discovers these templates:

| Template ID | Template Name | Description |
|-------------|---------------|-------------|
| `simple-test` | Simple Test Agent | Basic conversational agent for testing |
| `workflow` | Workflow Agent | Sequential step execution with state management |

### Template Discovery

Templates are discovered from:
- `runtime/infrastructure/frameworks/langgraph/templates/`
- Each template is a Python class extending `BaseLangGraphAgent`
- Templates are registered in `templates/__init__.py`

Use the helper script to see available templates:
```bash
python config/show-templates.py
```

### Creating Agents with Templates

When creating agents via the API, specify:

```bash
POST /v1/agents
{
  "name": "My Assistant",
  "template_id": "simple-test",  # Use discovered template ID
  "template_version": "v1.0.0",
  "configuration": {
    "system_message": "You are a helpful assistant",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

### Template-Specific Configuration

Each template defines its own configuration schema. Check the template class for available options:

- **Simple Test Agent**: Basic system message, temperature, max tokens
- **Workflow Agent**: Step definitions, parallel execution limits, retry policies

## 🔒 Security & Best Practices

### API Key Management

1. **Never commit API keys** to version control
2. **Use environment variables** for all sensitive data
3. **Use separate keys** for development/production
4. **Rotate keys regularly**

### Toolset Security

1. **Sandbox execution** - Enable for code execution tools
2. **Workspace isolation** - Limit filesystem access to safe directories
3. **Timeout limits** - Prevent runaway processes
4. **Input validation** - Validate all tool inputs

### Example Secure Configuration

```bash
# .env file
OPENAI_API_KEY=sk-proj-actual-key-here
SANDBOX_MODE=true
FILESYSTEM_ROOT=/safe/workspace
MAX_EXECUTION_TIME=30
ENABLE_RATE_LIMITING=true

# Services configuration
SERVICES_CONFIG_FILE=config/services-config.json
```

## 🔧 Troubleshooting

### Common Issues

#### 1. "Provider not found" errors
- Check that provider name in `default_provider` matches a key in `providers`
- Verify API key is set and not empty

#### 2. MCP server startup failures
- Install required packages: `npm install -g @modelcontextprotocol/server-*`
- Check server command paths and arguments
- Verify environment variables are set

#### 3. Tool execution timeouts
- Increase timeout values in toolset config
- Check network connectivity for API-based tools
- Monitor resource usage for local tools

#### 4. Configuration validation errors
- Use the validation script: `python config/validate-config.py`
- Use a JSON validator to check syntax
- Ensure all required fields are present
- Check that environment variable references use correct syntax: `${VAR_NAME}`

### Debug Mode

Enable debug mode for detailed logging:

```bash
# .env file
DEBUG=true
LOG_LEVEL=DEBUG
```

### Health Check

Check runtime health and configuration:

```bash
curl -H "Authorization: Bearer your-runtime-token" http://localhost:8000/v1/health
```

### Configuration Validation

Use the included validation script:

```bash
# Validate everything
python config/validate-config.py

# Validate specific config file
python config/validate-config.py config/services-config.json

# Show available templates with schemas
python config/show-templates.py --template simple-test
```

## 📚 Advanced Configuration

### Custom LLM Endpoints

For custom or self-hosted models:

```json
{
  "custom-llm": {
    "type": "openai",
    "model": "custom-model-name",
    "base_url": "http://your-llm-server:8080/v1",
    "api_key": "optional-if-needed",
    "temperature": 0.7,
    "max_tokens": 4000
  }
}
```

### Multiple Tool Instances

Run multiple instances of the same tool type:

```json
{
  "database-prod": {
    "type": "mcp",
    "config": {
      "servers": [
        {
          "name": "sqlite-prod",
          "command": "npx",
          "args": ["@modelcontextprotocol/server-sqlite", "/data/production.db"]
        }
      ]
    }
  },
  "database-test": {
    "type": "mcp", 
    "config": {
      "servers": [
        {
          "name": "sqlite-test",
          "command": "npx",
          "args": ["@modelcontextprotocol/server-sqlite", "/data/test.db"]
        }
      ]
    }
  }
}
```

### Environment-Specific Configurations

Use different configurations for different environments:

```bash
# Development
SERVICES_CONFIG_FILE=config/dev-config.json

# Production
SERVICES_CONFIG_FILE=config/prod-config.json

# Testing
SERVICES_CONFIG_FILE=config/test-config.json
```

### Template Development

To create a custom template:

```python
# In runtime/infrastructure/frameworks/langgraph/templates/
from .base import BaseLangGraphAgent

class MyCustomAgent(BaseLangGraphAgent):
    template_name = "My Custom Agent"
    template_id = "my-custom-agent"
    template_version = "1.0.0"
    template_description = "Custom agent for specific tasks"
    
    # Implement required methods...
```

Then register in `templates/__init__.py`:

```python
_TEMPLATE_CLASSES = {
    "simple-test": SimpleTestAgent,
    "workflow": WorkflowAgent,
    "my-custom-agent": MyCustomAgent,  # Add your template
}
```

## 🆘 Support

For issues and questions:

1. Check the [troubleshooting section](#-troubleshooting)
2. Review the [API documentation](../docs/api/)
3. Check agent runtime logs for error details
4. Verify your configuration against these examples

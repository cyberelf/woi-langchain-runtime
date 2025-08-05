# Agent Runtime API Specification

This document specifies the required API endpoints that any Agent Runtime service must implement to be compatible with the AI Platform. Agent Runtime services are responsible for executing agents, managing agent lifecycle, and providing dynamic configuration schemas.

## Overview

The Agent Runtime API enables:
- Agent lifecycle management (create, update, delete)
- Dynamic schema synchronization between runtime environments and the AI Platform
- OpenAI-compatible agent execution with conversation history
- Health monitoring and status reporting
- Version management and compatibility checking

## Architecture

The Agent Runtime serves as the **truth source** for:
- Agent template definitions and schemas
- Agent execution logic and behavior
- Agent lifecycle management

The Backend serves as the **truth source** for:
- Agent metadata and configuration
- User management and permissions
- Agent orchestration and workflow

## Base URL

The base URL for the Agent Runtime service is configured in each runtime's `url` field in the AI Platform.

## Authentication

All API requests must include a runtime token in the `X-Runtime-Token` header:

```
X-Runtime-Token: <runtime_token>
```

The runtime token is configured in each runtime's `token` field and is used for mutual authentication between the AI Platform and the runtime service.

## API Endpoints

### Agent Management

#### Create Agent

Creates a new agent in the runtime environment.

**URL**: `/v1/agents`

**Method**: `POST`

**Headers**:

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-Runtime-Token` | string | Yes | Runtime authentication token |
| `Content-Type` | string | Yes | Must be `application/json` |

**Request Body**:

```json
{
  "id": "agent-123",
  "name": "Customer Service Agent",
  "description": "Handles basic customer inquiries",
  "type": "task",
  "template_id": "template-456",
  "template_version_id": "version-789",
  "template_config": {
    "taskSteps": {
      "steps": ["Greet", "Identify issue", "Resolve or escalate"],
      "stepTimeout": 300,
      "retryCount": 2
    }
  },
  "system_prompt": "You are a helpful customer service agent...",
  "conversation_config": {
    "continuous": true,
    "historyLength": 5
  },
  "toolsets": ["web-search", "knowledge-base-1"],
  "llm_config_id": "llm-config-123",
  "agent_line_id": "agent-line-456",
  "version_type": "beta",
  "version_number": "v1",
  "owner_id": "user-789",
  "status": "draft"
}
```

**Request Body Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Agent line ID (logical identifier) |
| `name` | string | Yes | Agent name |
| `description` | string | No | Agent description |
| `avatar_url` | string | No | Agent avatar URL |
| `type` | string | Yes | Agent type |
| `template_id` | string | Yes | Template type identifier |
| `template_version_id` | string | Yes | Template version string |
| `template_config` | object | No | Template configuration |
| `system_prompt` | string | No | System prompt |
| `conversation_config` | object | No | Conversation configuration |
| `toolsets` | array | No | Available toolsets |
| `llm_config_id` | string | No | LLM configuration ID |
| `agent_line_id` | string | Yes | Agent line ID |
| `version_type` | string | No | Version type: beta or release (default: beta) |
| `version_number` | string | No | Version number: 'v1', 'v2', etc. (default: beta) |
| `owner_id` | string | Yes | Agent owner ID for beta access control |
| `status` | string | No | Agent status: draft, submitted, pending, published, revoked (default: draft) |

**Response**:

```json
{
  "success": true,
  "agent_id": "agent-123",
  "message": "Agent created successfully",
  "validation_results": {
    "valid": true,
    "warnings": []
  }
}
```

**Status Codes**:

- `201 Created`: Agent created successfully
- `400 Bad Request`: Invalid agent configuration
- `401 Unauthorized`: Invalid or missing runtime token
- `409 Conflict`: Agent with same ID already exists
- `422 Unprocessable Entity`: Agent configuration validation failed
- `500 Internal Server Error`: Runtime error

#### Update Agent

Updates an existing agent in the runtime environment.

**URL**: `/v1/agents/{agent_id}`

**Method**: `PUT`

**Headers**:

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-Runtime-Token` | string | Yes | Runtime authentication token |
| `Content-Type` | string | Yes | Must be `application/json` |

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | Yes | Unique identifier of the agent to update |

**Request Body**: Same as create agent (partial updates allowed)

**Response**:

```json
{
  "success": true,
  "agent_id": "agent-123",
  "message": "Agent updated successfully",
  "validation_results": {
    "valid": true,
    "warnings": [
      "Template version changed, some configurations may need adjustment"
    ]
  }
}
```

**Status Codes**:

- `200 OK`: Agent updated successfully
- `400 Bad Request`: Invalid agent configuration
- `401 Unauthorized`: Invalid or missing runtime token
- `404 Not Found`: Agent not found
- `422 Unprocessable Entity`: Agent configuration validation failed
- `500 Internal Server Error`: Runtime error

#### Delete Agent

Deletes an agent from the runtime environment.

**URL**: `/v1/agents/{agent_id}`

**Method**: `DELETE`

**Headers**:

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-Runtime-Token` | string | Yes | Runtime authentication token |

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | Yes | Unique identifier of the agent to delete |

**Response**:

```json
{
  "success": true,
  "agent_id": "agent-123",
  "message": "Agent deleted successfully"
}
```

**Status Codes**:

- `200 OK`: Agent deleted successfully
- `401 Unauthorized`: Invalid or missing runtime token
- `404 Not Found`: Agent not found
- `500 Internal Server Error`: Runtime error

### Get Runtime Schema

Retrieves the current configuration schema supported by the runtime. This endpoint is called by the backend during runtime synchronization to fetch the latest schema and update the runtime's version and status.

**URL**: `/v1/schema`

**Method**: `GET`

**Headers**:

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-Runtime-Token` | string | Yes | Runtime authentication token |
| `X-Schema-Version` | string | No | Client's current schema version for compatibility checking |

**Response**:

```json
{
  "version": "1.2.0",
  "lastUpdated": "2024-03-20T10:00:00Z",
  "supportedAgentTemplates": [
    {
      "template_name": "智能客服助手",
      "template_id": "customer-service-bot",
      "version": "1.0.0",
              "configSchema": {
          "template_name": "智能客服助手",
          "template_id": "customer-service-bot",
          "sections": [
            {
              "id": "conversation",
              "title": "对话设置",
              "description": "配置智能体的对话行为",
              "fields": [
                {
                  "id": "continuous",
                  "type": "checkbox",
                  "label": "持续对话模式",
                  "description": "启用持续对话以保持上下文连贯性",
                  "defaultValue": true
                },
                {
                  "id": "historyLength",
                  "type": "number",
                  "label": "对话历史长度",
                  "description": "保留的最大历史消息数量",
                  "defaultValue": 10,
                  "validation": {
                    "min": 5,
                    "max": 100
                  }
                }
              ]
            }
          ]
        },
    },
    {
      "type": "task",
      "version": "1.1.0",
      "displayName": "任务型智能体",
      "description": "Structured task execution agent with step-by-step processing",
      "configSchema": {
        "type": "object",
        "properties": {
          "taskSteps": {
            "type": "object",
            "title": "任务步骤",
            "properties": {
              "steps": {
                "type": "array",
                "title": "执行步骤",
                "description": "任务执行的步骤列表",
                "items": {
                  "type": "string"
                },
                "minItems": 1,
                "maxItems": 20
              },
              "stepTimeout": {
                "type": "integer",
                "title": "步骤超时",
                "description": "每个步骤的超时时间（秒）",
                "minimum": 10,
                "maximum": 3600,
                "default": 300
              },
              "retryCount": {
                "type": "integer",
                "title": "重试次数",
                "description": "步骤失败时的重试次数",
                "minimum": 0,
                "maximum": 5,
                "default": 2
              },
              "parallelExecution": {
                "type": "boolean",
                "title": "并行执行",
                "description": "是否允许步骤并行执行",
                "default": false
              }
            },
            "required": ["steps"]
          },
          "validation": {
            "type": "object",
            "title": "验证设置",
            "properties": {
              "strictMode": {
                "type": "boolean",
                "title": "严格模式",
                "description": "是否启用严格验证模式",
                "default": true
              },
              "outputFormat": {
                "type": "string",
                "title": "输出格式",
                "enum": ["json", "text", "structured"],
                "default": "structured"
              }
            }
          }
        },
        "required": ["taskSteps"]
      },
      
    },
    {
      "type": "custom",
      "version": "1.0.0",
      "displayName": "自定义智能体",
      "description": "Custom agent with user-defined code and behavior",
      "configSchema": {
        "type": "object",
        "properties": {
          "codeSource": {
            "type": "object",
            "title": "代码源",
            "properties": {
              "type": {
                "type": "string",
                "title": "代码类型",
                "enum": ["inline", "repository", "package"],
                "default": "inline"
              },
              "content": {
                "type": "string",
                "title": "代码内容",
                "description": "内联代码或代码引用"
              },
              "entryPoint": {
                "type": "string",
                "title": "入口点",
                "description": "代码执行的入口函数",
                "default": "main"
              },
              "dependencies": {
                "type": "array",
                "title": "依赖包",
                "items": {
                  "type": "string"
                }
              }
            },
            "required": ["type", "content"]
          },
          "runtime": {
            "type": "object",
            "title": "运行时设置",
            "properties": {
              "language": {
                "type": "string",
                "title": "编程语言",
                "enum": ["python", "javascript", "typescript"],
                "default": "python"
              },
              "version": {
                "type": "string",
                "title": "语言版本",
                "description": "编程语言版本"
              },
              "timeout": {
                "type": "integer",
                "title": "执行超时",
                "description": "代码执行超时时间（秒）",
                "minimum": 1,
                "maximum": 300,
                "default": 30
              },
              "memoryLimit": {
                "type": "integer",
                "title": "内存限制",
                "description": "内存限制（MB）",
                "minimum": 64,
                "maximum": 2048,
                "default": 512
              }
            },
            "required": ["language"]
          }
        },
        "required": ["codeSource", "runtime"]
      },
    }
  ],
  "capabilities": {
    "streaming": true,
    "toolCalling": true,
    "multimodal": false,
    "codeExecution": true
  },
  "limits": {
    "maxConcurrentAgents": 100,
    "maxMessageLength": 32000,
    "maxConversationHistory": 100
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Semantic version of the runtime schema |
| `lastUpdated` | string | ISO8601 timestamp of last schema update |
| `supportedAgentTemplates` | array | List of agent templates supported by this runtime |
| `supportedAgentTemplates[].template_name` | string | Human-readable name for the template |
| `supportedAgentTemplates[].template_id` | string | Template identifier (customer-service-bot, task-execution-bot, etc.) |
| `supportedAgentTemplates[].version` | string | Version of this template implementation |
| `supportedAgentTemplates[].configSchema` | object | Template configuration schema with sections and fields |
| `capabilities` | object | Runtime capabilities and features |
| `limits` | object | Runtime limits and constraints |

**Status Codes**:

- `200 OK`: Schema retrieved successfully
- `401 Unauthorized`: Invalid or missing runtime token
- `409 Conflict`: Schema version mismatch (when X-Schema-Version header is provided)
- `500 Internal Server Error`: Runtime error

**Version Mismatch Response** (409):
```json
{
  "error": "VERSION_MISMATCH",
  "message": "Incompatible schema version",
  "current_version": "1.2.0",
  "required_version": "1.1.0",
  "breaking_changes": [
    "Removed deprecated 'legacy_mode' configuration",
    "Changed 'timeout' field from seconds to milliseconds"
  ]
}
```

### Execute Agent (OpenAI Compatible)

Executes an agent using OpenAI-compatible chat completions format.

**URL**: `/v1/chat/completions`

**Method**: `POST`

**Headers**:

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-Runtime-Token` | string | Yes | Runtime authentication token |
| `Content-Type` | string | Yes | Must be `application/json` |

**Request Body** (OpenAI Compatible):

```json
{
  "model": "agent-123",
  "messages": [
    {
      "role": "user",
      "content": "Hello, I need help with my order"
    }
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 1000,
  "metadata": {
    "session_id": "session-456",
    "user_id": "user-789"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | Agent ID to execute |
| `messages` | array | Yes | Conversation messages in OpenAI format |
| `stream` | boolean | No | Whether to stream the response (default: false) |
| `temperature` | number | No | Sampling temperature (0.0-2.0) |
| `max_tokens` | integer | No | Maximum tokens to generate |
| `metadata` | object | No | Additional execution metadata |

**Response** (OpenAI Compatible):

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "agent-123",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'd be happy to help you with your order. Could you please provide your order number?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 20,
    "total_tokens": 32
  },
  "metadata": {
    "agent_id": "agent-123",
    "agent_type": "task",
    "processing_time_ms": 150,
    "execution_steps": [
      {
        "step": "greet",
        "status": "completed",
        "duration_ms": 50
      }
    ],
    "tools_used": ["web-search"],
    "confidence_score": 0.92
  }
}
```

**Streaming Response**:

When `stream: true`, the response is sent as Server-Sent Events:

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{"content":"! I'd be"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{"content":" happy to help"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":12,"completion_tokens":20,"total_tokens":32}}

data: [DONE]
```

**Status Codes**:

- `200 OK`: Agent executed successfully
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Invalid or missing runtime token
- `404 Not Found`: Agent not found
- `408 Request Timeout`: Agent execution timed out
- `422 Unprocessable Entity`: Invalid parameters
- `500 Internal Server Error`: Runtime execution error

### Health Check

Checks the health and status of the runtime service.

**URL**: `/v1/health`

**Method**: `GET`

**Headers**:

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-Runtime-Token` | string | Yes | Runtime authentication token |

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2024-03-20T10:00:00Z",
  "version": "1.2.0",
  "uptime_seconds": 86400,
  "last_sync": "2024-03-20T09:30:00Z",
  "checks": {
    "llm_proxy": {
      "status": "healthy",
      "response_time_ms": 150,
      "last_check": "2024-03-20T09:59:30Z"
    },
    "database": {
      "status": "healthy",
      "response_time_ms": 5,
      "last_check": "2024-03-20T09:59:30Z"
    },
    "agent_templates": {
      "status": "healthy",
      "loaded_templates": 15,
      "last_check": "2024-03-20T09:59:30Z"
    }
  },
  "metrics": {
    "active_agents": 42,
    "total_executions": 1250,
    "average_response_time_ms": 320,
    "error_rate": 0.02
  }
}
```

**Status Codes**:

- `200 OK`: Health check successful
- `401 Unauthorized`: Invalid or missing runtime token
- `503 Service Unavailable`: Runtime is unhealthy

## Backend-to-Runtime Communication

The AI Platform backend communicates with runtime services for schema synchronization and agent management. All communication uses the `X-Runtime-Token` authentication header.

### Runtime Schema Synchronization

The backend periodically syncs with runtime services to fetch the latest configuration schemas and update runtime status. This is triggered through the backend's runtime management API.

**Backend Runtime Sync Endpoint**:

```http
POST /v1/runtimes/{runtime_id}/sync
Authorization: Bearer {backend_jwt_token}
```

**Backend Sync Process**:

1. **Backend** receives sync request from frontend/admin
2. **Backend** makes HTTP request to runtime's `/v1/schema` endpoint using `X-Runtime-Token` authentication
3. **Runtime** returns schema information including version and supported agent types
4. **Backend** updates runtime record with new version and sets status to "active"
5. **Backend** returns sync result to client

**Runtime Schema Request** (made by backend):

```http
GET /v1/schema
X-Runtime-Token: {runtime_token}
```

**Backend Sync Result Response**:

```json
{
  "success": true,
  "newVersion": "1.3.0",
  "error": null
}
```

**Error Response** (when sync fails):

```json
{
  "success": false,
  "newVersion": null,
  "error": "HTTP error: Client error '401 Unauthorized' for url 'https://runtime.example.com/v1/schema'"
}
```

### Authentication Details

- **Backend-to-Runtime**: Uses `X-Runtime-Token` header with the token configured in runtime registration
- **Client-to-Backend**: Uses `Authorization: Bearer {jwt_token}` for user authentication
- **Runtime Token**: Configured during runtime registration and used for all backend-to-runtime communication

### Error Handling in Sync

Common sync errors and their meanings:

- **401 Unauthorized**: Runtime token is invalid or expired
- **Connection Timeout**: Runtime service is unreachable
- **404 Not Found**: Runtime schema endpoint not found
- **Invalid JSON**: Runtime returned malformed response
- **Schema Validation**: Runtime schema doesn't match expected format

When sync fails, the runtime status is updated to "error" and the error message is returned in the response.

## Error Handling

All error responses follow a consistent format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "specific_field",
    "code": "validation_error",
    "additional_info": "..."
  }
}
```

### Common Error Codes

- `INVALID_TOKEN`: Invalid or missing runtime token
- `AGENT_NOT_FOUND`: Requested agent does not exist
- `VALIDATION_ERROR`: Request validation failed
- `EXECUTION_ERROR`: Agent execution failed
- `TIMEOUT_ERROR`: Request timed out
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Internal server error

## Performance Requirements

- **Response Time**: 95th percentile under 2 seconds for agent execution
- **Throughput**: Support at least 100 concurrent agent executions
- **Availability**: 99.9% uptime SLA
- **Scalability**: Horizontal scaling support

## Security Considerations

- All communications must use HTTPS
- Runtime tokens must be securely stored and rotated regularly
- Input validation and sanitization for all requests
- Rate limiting to prevent abuse
- Audit logging for all agent operations

## Implementation Guidelines

### Agent Lifecycle

1. **Creation**: Validate agent configuration against template schema
2. **Updates**: Support partial updates, validate changes
3. **Deletion**: Clean up all agent resources and state
4. **Execution**: Use LLM Proxy for model calls, maintain conversation state

### LLM Integration

- Use LLM Proxy Service for all model calls
- Include `llm_config_id` in requests to LLM Proxy
- Handle rate limiting and retries gracefully
- Support streaming responses when requested

### Error Recovery

- Implement circuit breakers for external dependencies
- Graceful degradation when LLM Proxy is unavailable
- Retry logic with exponential backoff
- Comprehensive error logging and monitoring

## Testing

### Unit Tests
- Agent configuration validation
- Message processing logic
- Error handling scenarios

### Integration Tests
- End-to-end agent execution
- LLM Proxy integration
- Health check functionality

### Performance Tests
- Load testing with concurrent executions
- Stress testing with high message volumes
- Latency testing for response times

## Deployment

### Environment Variables
- `RUNTIME_TOKEN`: Authentication token
- `LLM_PROXY_URL`: LLM Proxy service endpoint
- `DATABASE_URL`: Database connection string
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARN, ERROR)

### Health Checks
- Kubernetes readiness and liveness probes
- Load balancer health checks
- Monitoring and alerting setup

### Scaling
- Horizontal pod autoscaling based on CPU/memory
- Connection pooling for database
- Caching for frequently accessed data

## Monitoring

### Metrics
- Request rate and response times
- Error rates by endpoint
- Agent execution success/failure rates
- Resource utilization (CPU, memory, disk)

### Logging
- Structured logging in JSON format
- Request/response logging with correlation IDs
- Error logging with stack traces
- Performance logging for slow operations

### Alerting
- High error rates
- Slow response times
- Service unavailability
- Resource exhaustion 
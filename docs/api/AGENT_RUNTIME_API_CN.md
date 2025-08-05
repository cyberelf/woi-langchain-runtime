# 智能体运行时 API 规范

本文档规定了任何智能体运行时服务必须实现的 API 端点，以便与 AI 平台兼容。智能体运行时服务负责执行智能体、管理智能体生命周期并提供动态配置模式。

## 概述

智能体运行时 API 支持：
- 智能体模板生命周期管理（创建、更新、删除）
- 运行时环境与 AI 平台之间的动态模式同步
- 兼容 OpenAI 的智能体执行和对话历史
- 健康监控和状态报告
- 版本管理和兼容性检查

## 架构

智能体运行时作为以下内容的**真实数据源**：
- 智能体模板定义和模式
- 智能体执行逻辑和行为
- 智能体模板的生命周期管理

后端作为以下内容的**真实数据源**：
- 智能体配置
- 用户管理和权限
- 智能体编排和工作流

## 基础 URL

智能体运行时服务的基础 URL 在 AI 平台中每个运行时的 `url` 字段中配置。

## 认证

所有 API 请求必须在 `X-Runtime-Token` 头中包含运行时令牌：

```
X-Runtime-Token: <runtime_token>
```

运行时令牌在每个运行时的 `token` 字段中配置，用于 AI 平台和运行时服务之间的相互认证。

## API 端点

### 智能体管理

#### 创建智能体

在运行时环境中创建新的智能体。

**URL**: `/v1/agents`

**方法**: `POST`

**请求头**:

| 头部 | 类型 | 必需 | 描述 |
|--------|------|------|-------------|
| `X-Runtime-Token` | string | 是 | 运行时认证令牌 |
| `Content-Type` | string | 是 | 必须为 `application/json` |

**请求体**:

```json
{
  "id": "agent-123",
  "name": "客服智能体",
  "description": "处理基本客户咨询",
  "type": "task",
  "avatar_url": "https://...",
  "template_id": "template-456",
  "template_version_id": "version-789",
  "template_config": {
    "taskSteps": {
      "steps": ["问候", "识别问题", "解决或升级"],
      "stepTimeout": 300,
      "retryCount": 2
    }
  },
  "system_prompt": "你是一个有用的客服智能体...",
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

**请求体字段**:

| 字段 | 类型 | 必需 | 描述 |
|-------|------|------|-------------|
| `id` | string | 是 | 智能体的唯一标识符 |
| `name` | string | 是 | 智能体名称 |
| `description` | string | 否 | 智能体描述 |
| `avatar_url` | string | 否 | 智能体头像URL |
| `type` | string | 是 | 智能体类型 |
| `template_id` | string | 是 | 模板类型标识符 |
| `template_version_id` | string | 是 | 模板版本字符串 |
| `template_config` | object | 否 | 模板配置 |
| `system_prompt` | string | 否 | 系统提示词 |
| `conversation_config` | object | 否 | 对话配置 |
| `toolsets` | array | 否 | 可用工具集 |
| `llm_config_id` | string | 否 | LLM配置ID |
| `agent_line_id` | string | 是 | 智能体线路ID |
| `version_type` | string | 否 | 版本类型：beta 或 release（默认：beta） |
| `version_number` | string | 否 | 版本号：'v1', 'v2' 等（默认：beta） |
| `owner_id` | string | 是 | 智能体所有者ID，用于beta访问控制 |
| `status` | string | 否 | 智能体状态：draft, submitted, pending, published, revoked（默认：draft） |

**响应**:

```json
{
  "success": true,
  "agent_id": "agent-123",
  "message": "智能体创建成功",
  "validation_results": {
    "valid": true,
    "warnings": []
  }
}
```

**状态码**:

- `201 Created`: 智能体创建成功
- `400 Bad Request`: 无效的智能体配置
- `401 Unauthorized`: 无效或缺失的运行时令牌
- `409 Conflict`: 相同 ID 的智能体已存在
- `422 Unprocessable Entity`: 智能体配置验证失败
- `500 Internal Server Error`: 运行时错误

#### 更新智能体

更新运行时环境中的现有智能体。

**URL**: `/v1/agents/{agent_id}`

**方法**: `PUT`

**请求头**:

| 头部 | 类型 | 必需 | 描述 |
|--------|------|------|-------------|
| `X-Runtime-Token` | string | 是 | 运行时认证令牌 |
| `Content-Type` | string | 是 | 必须为 `application/json` |

**路径参数**:

| 参数 | 类型 | 必需 | 描述 |
|-----------|------|------|-------------|
| `agent_id` | string | 是 | 要更新的智能体的唯一标识符 |

**请求体**（支持部分更新）:

```json
{
  "name": "更新后的客服智能体",
  "description": "更新后的客服智能体描述",
  "type": "task",
  "avatar_url": "https://...",
  "template_id": "template-456",
  "template_version_id": "version-789",
  "template_config": {
    "taskSteps": {
      "steps": ["问候", "识别问题", "解决或升级"],
      "stepTimeout": 300,
      "retryCount": 2
    }
  },
  "system_prompt": "你是一个有用的客服智能体...",
  "conversation_config": {
    "continuous": true,
    "historyLength": 5
  },
  "toolsets": ["web-search", "knowledge-base-1"],
  "selected_tool_sets": ["web-search"],
  "llm_config_id": "llm-config-123",
  "agent_line_id": "agent-line-456",
  "version_type": "release",
  "version_number": "v2",
  "owner_id": "user-789",
  "status": "published"
}
```

**响应**:

```json
{
  "success": true,
  "agent_id": "agent-123",
  "message": "智能体更新成功",
  "validation_results": {
    "valid": true,
    "warnings": [
      "模板版本已更改，某些配置可能需要调整"
    ]
  }
}
```

**状态码**:

- `200 OK`: 智能体更新成功
- `400 Bad Request`: 无效的智能体配置
- `401 Unauthorized`: 无效或缺失的运行时令牌
- `404 Not Found`: 智能体未找到
- `422 Unprocessable Entity`: 智能体配置验证失败
- `500 Internal Server Error`: 运行时错误

#### 删除智能体

从运行时环境中删除智能体。

**URL**: `/v1/agents/{agent_id}`

**方法**: `DELETE`

**请求头**:

| 头部 | 类型 | 必需 | 描述 |
|--------|------|------|-------------|
| `X-Runtime-Token` | string | 是 | 运行时认证令牌 |

**路径参数**:

| 参数 | 类型 | 必需 | 描述 |
|-----------|------|------|-------------|
| `agent_id` | string | 是 | 要删除的智能体的唯一标识符 |

**响应**:

```json
{
  "success": true,
  "agent_id": "agent-123",
  "message": "智能体删除成功"
}
```

**状态码**:

- `200 OK`: 智能体删除成功
- `401 Unauthorized`: 无效或缺失的运行时令牌
- `404 Not Found`: 智能体未找到
- `500 Internal Server Error`: 运行时错误

### 获取运行时模式

检索运行时支持的当前配置模式。

**URL**: `/v1/schema`

**方法**: `GET`

**请求头**:

| 头部 | 类型 | 必需 | 描述 |
|--------|------|------|-------------|
| `X-Runtime-Token` | string | 是 | 运行时认证令牌 |
| `X-Schema-Version` | string | 否 | 客户端当前模式版本，用于兼容性检查 |

**响应**:

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
      "description": "具有逐步处理的结构化任务执行智能体",
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
      "description": "具有用户定义代码和行为的自定义智能体",
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

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `version` | string | 运行时模式的语义版本 |
| `lastUpdated` | string | 最后模式更新的 ISO8601 时间戳 |
| `supportedAgentTemplates` | array | 此运行时支持的智能体模板列表 |
| `supportedAgentTemplates[].template_name` | string | 模板的人类可读名称 |
| `supportedAgentTemplates[].template_id` | string | 模板标识符（customer-service-bot、task-execution-bot等） |
| `supportedAgentTemplates[].version` | string | 此模板实现的版本 |
| `supportedAgentTemplates[].configSchema` | object | 包含节和字段的模板配置架构 |
| `capabilities` | object | 运行时能力和功能 |
| `limits` | object | 运行时限制和约束 |

**状态码**:

- `200 OK`: 模式检索成功
- `401 Unauthorized`: 无效或缺失的运行时令牌
- `409 Conflict`: 模式版本不匹配（当提供 X-Schema-Version 头时）
- `500 Internal Server Error`: 运行时错误

**版本不匹配响应** (409):
```json
{
  "error": "VERSION_MISMATCH",
  "message": "不兼容的模式版本",
  "current_version": "1.2.0",
  "required_version": "1.1.0",
  "breaking_changes": [
    "移除了已弃用的 'legacy_mode' 配置",
    "将 'timeout' 字段从秒改为毫秒"
  ]
}
```

### 执行智能体（兼容 OpenAI）

使用兼容 OpenAI 的聊天完成格式执行智能体。

**URL**: `/v1/chat/completions`

**方法**: `POST`

**请求头**:

| 头部 | 类型 | 必需 | 描述 |
|--------|------|------|-------------|
| `X-Runtime-Token` | string | 是 | 运行时认证令牌 |
| `Content-Type` | string | 是 | 必须为 `application/json` |

**请求体**（兼容 OpenAI）:

```json
{
  "model": "agent-123",
  "messages": [
    {
      "role": "user",
      "content": "你好，我需要帮助处理我的订单"
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

| 字段 | 类型 | 必需 | 描述 |
|-------|------|------|-------------|
| `model` | string | 是 | 要执行的智能体 ID |
| `messages` | array | 是 | OpenAI 格式的对话消息 |
| `stream` | boolean | 否 | 是否流式传输响应（默认：false） |
| `temperature` | number | 否 | 采样温度（0.0-2.0） |
| `max_tokens` | integer | 否 | 生成的最大令牌数 |
| `metadata` | object | 否 | 额外的执行元数据 |

**响应**（兼容 OpenAI）:

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
        "content": "你好！我很乐意帮助你处理订单。请提供你的订单号码好吗？"
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

**流式响应**:

当 `stream: true` 时，响应以服务器发送事件的形式发送：

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{"role":"assistant","content":"你好"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{"content":"！我很"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{"content":"乐意帮助"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"agent-123","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":12,"completion_tokens":20,"total_tokens":32}}

data: [DONE]
```

**状态码**:

- `200 OK`: 智能体执行成功
- `400 Bad Request`: 无效的请求格式
- `401 Unauthorized`: 无效或缺失的运行时令牌
- `404 Not Found`: 智能体未找到
- `408 Request Timeout`: 智能体执行超时
- `422 Unprocessable Entity`: 无效参数
- `500 Internal Server Error`: 运行时执行错误

### 健康检查

检查运行时服务的健康状态。

**URL**: `/v1/health`

**方法**: `GET`

**请求头**:

| 头部 | 类型 | 必需 | 描述 |
|--------|------|------|-------------|
| `X-Runtime-Token` | string | 是 | 运行时认证令牌 |

**响应**:

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

**状态码**:

- `200 OK`: 健康检查成功
- `401 Unauthorized`: 无效或缺失的运行时令牌
- `503 Service Unavailable`: 运行时不健康

## 后端与运行时通信

AI 平台后端与运行时服务进行模式同步和智能体管理通信。所有通信都使用 `X-Runtime-Token` 认证头。

### 运行时模式同步

后端定期与运行时服务同步，获取最新的配置模式并更新运行时状态。这通过后端的运行时管理 API 触发。

**后端运行时同步端点**:

```http
POST /v1/runtimes/{runtime_id}/sync
Authorization: Bearer {backend_jwt_token}
```

**后端同步流程**:

1. **后端** 接收来自前端/管理员的同步请求
2. **后端** 使用 `X-Runtime-Token` 认证向运行时的 `/v1/schema` 端点发起 HTTP 请求
3. **运行时** 返回包含版本和支持的智能体类型的模式信息
4. **后端** 使用新版本更新运行时记录并将状态设置为"active"
5. **后端** 向客户端返回同步结果

**运行时模式请求**（由后端发起）:

```http
GET /v1/schema
X-Runtime-Token: {runtime_token}
```

**后端同步结果响应**:

```json
{
  "success": true,
  "newVersion": "1.3.0",
  "error": null
}
```

**错误响应**（当同步失败时）:

```json
{
  "success": false,
  "newVersion": null,
  "error": "HTTP error: Client error '401 Unauthorized' for url 'https://runtime.example.com/v1/schema'"
}
```

### 认证详情

- **后端到运行时**: 使用 `X-Runtime-Token` 头，令牌在运行时注册时配置
- **客户端到后端**: 使用 `Authorization: Bearer {jwt_token}` 进行用户认证
- **运行时令牌**: 在运行时注册期间配置，用于所有后端到运行时的通信

### 同步中的错误处理

常见同步错误及其含义：

- **401 Unauthorized**: 运行时令牌无效或已过期
- **Connection Timeout**: 运行时服务不可达
- **404 Not Found**: 运行时模式端点未找到
- **Invalid JSON**: 运行时返回格式错误的响应
- **Schema Validation**: 运行时模式不符合预期格式

当同步失败时，运行时状态会更新为"error"，错误消息会在响应中返回。

## 错误处理

所有错误响应遵循一致的格式：

```json
{
  "error": "ERROR_CODE",
  "message": "人类可读的错误消息",
  "details": {
    "field": "specific_field",
    "code": "validation_error",
    "additional_info": "..."
  }
}
```

### 常见错误代码

- `INVALID_TOKEN`: 无效或缺失的运行时令牌
- `AGENT_NOT_FOUND`: 请求的智能体不存在
- `VALIDATION_ERROR`: 请求验证失败
- `EXECUTION_ERROR`: 智能体执行失败
- `TIMEOUT_ERROR`: 请求超时
- `RATE_LIMIT_EXCEEDED`: 请求过多
- `INTERNAL_ERROR`: 内部服务器错误

## 性能要求

- **响应时间**: 智能体执行的第 95 百分位数在 2 秒以下
- **吞吐量**: 支持至少 100 个并发智能体执行
- **可用性**: 99.9% 正常运行时间 SLA
- **可扩展性**: 水平扩展支持

## 安全考虑

- 所有通信必须使用 HTTPS
- 运行时令牌必须安全存储并定期轮换
- 对所有请求进行输入验证和清理
- 实施速率限制以防止滥用
- 对所有智能体操作进行审计日志记录

## 实施指南

### 智能体生命周期

1. **创建**: 根据模板模式验证智能体配置
2. **更新**: 支持部分更新，验证更改
3. **删除**: 清理所有智能体资源和状态
4. **执行**: 使用 LLM 代理进行模型调用，维护对话状态

### LLM 集成

- 使用 LLM 代理服务进行所有模型调用
- 在对 LLM 代理的请求中包含 `llm_config_id`
- 优雅地处理速率限制和重试
- 在请求时支持流式响应

### 错误恢复

- 为外部依赖实施断路器
- 当 LLM 代理不可用时优雅降级
- 使用指数退避的重试逻辑
- 全面的错误日志记录和监控

## 测试

### 单元测试
- 智能体配置验证
- 消息处理逻辑
- 错误处理场景

### 集成测试
- 端到端智能体执行
- LLM 代理集成
- 健康检查功能

### 性能测试
- 并发执行的负载测试
- 高消息量的压力测试
- 响应时间的延迟测试

## 部署

### 环境变量
- `RUNTIME_TOKEN`: 认证令牌
- `LLM_PROXY_URL`: LLM 代理服务端点
- `DATABASE_URL`: 数据库连接字符串
- `LOG_LEVEL`: 日志级别（DEBUG、INFO、WARN、ERROR）

### 健康检查
- Kubernetes 就绪和存活探针
- 负载均衡器健康检查
- 监控和警报设置

### 扩展
- 基于 CPU/内存的水平 Pod 自动扩展
- 数据库连接池
- 频繁访问数据的缓存

## 监控

### 指标
- 请求速率和响应时间
- 按端点的错误率
- 智能体执行成功/失败率
- 资源利用率（CPU、内存、磁盘）

### 日志记录
- JSON 格式的结构化日志记录
- 带有关联 ID 的请求/响应日志记录
- 带有堆栈跟踪的错误日志记录
- 慢操作的性能日志记录

### 警报
- 高错误率
- 慢响应时间
- 服务不可用
- 资源耗尽 
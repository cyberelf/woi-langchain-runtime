# 智能体 API 集成文档

##  概述

本文档用于指导开发者如何将智能体服务集成至第三方应用中。通过以下接口，您可以完成身份认证、会话管理及流式对话等功能。

------

## 🔐 1. 身份认证（Token 获取）

所有接口均需使用 JWT 格式的 Token 进行身份验证。

### 获取方式：

在智能体页面点击 **“获取 Token”** 按钮，复制生成的 JWT Token。

> ⚠️ 注意：后续所有接口请求均需在请求头中携带该 Token。

------

token的生成规则：

1. 慧易加上expire_in参数，生成token，token默认一年过期

2. 开发者平台加上接口，使用web_token和app_id（运行时的app_id）调用慧易的生成token接口。



## 🧾 2. 会话管理

### 2.1 创建新会话

#### 接口地址

```
POST /chat/chat_record
```

#### 请求头

http

复制

```http
Content-Type: application/json
Authorization: Bearer <your_jwt_token>
```

#### 请求体

JSON

复制

```json
{
  "name": "你好",
  "agent_id": 1,
  "project_id": 97
}
```

#### 响应示例

JSON

复制

```json
{
  "rc": "success",
  "message": "Success",
  "data": 129
}
```

> ✅ `data` 字段即为新创建的会话 ID（`chat_id`）

------

### 2.2 获取会话列表

#### 接口地址

```
GET /chat/chat_record/list
```

#### 请求头

http

复制

```http
Content-Type: application/json
Authorization: Bearer <your_jwt_token>
```

#### 查询参数

表格

复制

| 参数名   | 类型 | 必填 | 说明      |
| :------- | :--- | :--- | :-------- |
| agent_id | int  | 是   | 智能体 ID |

#### 响应示例

JSON

复制

```json
{
  "rc": "success",
  "message": "Success",
  "data": {
    "list": [
      {
        "id": 67,
        "name": "你好",
        "user_id": 7,
        "agent_id": 1,
        "logic_agent_id": 97,
        "mcp_server_id": null,
        "mcp_server_name": null,
        "model_id": 3,
        "model_name": "qwen-plus",
        "search_enabled": false,
        "thinking_enabled": false,
        "created_time": "2025-06-24 17:01:44",
        "updated_time": "2025-06-24 17:01:44"
      }
    ],
    "current_page": 1,
    "page_size": 100,
    "total": 8
  }
}
```

------

## 💬 3. 对话接口

### 3.1 流式对话接口

#### 接口地址

```
POST /agent/{agent_name}/stream
```

> 📌 `agent_name` 需替换为实际的智能体名称。

#### 请求头

http

复制

```http
Content-Type: application/json
Authorization: <your_jwt_token>
```

#### 请求体

JSON

复制

```json
{
  "input": {
    "prompt": "你好",
    "ref_file_ids": []
  },
  "config": {
    "configurable": {
      "chat_id": 129,
      "project_id": 97
    }
  }
}
```

#### 响应格式

- 类型：`Server-Sent Events (SSE)`
- 编码：`UTF-8`

#### 响应示例

```
event: metadata
data: {"chat_id": "129", "question_id": "483"}

event: data
data: {"agent_id": 97, "chat_history_id": 483, "search_results": [], "reference": [], "feedback_support": 0, "similar_query": 0, "similar_query_list": [], "msgtype": "markdown", "markdown": {"content": "", "reasoning_content": "\n"}}

event: data
data: {"agent_id": 97, "chat_history_id": 483, "search_results": [], "reference": [], "feedback_support": 0, "similar_query": 0, "similar_query_list": [], "msgtype": "markdown", "markdown": {"content": "", "reasoning_content": "你"}}

event: data
data: {"agent_id": 97, "chat_history_id": 483, "search_results": [], "reference": [], "feedback_support": 0, "similar_query": 0, "similar_query_list": [], "msgtype": "markdown", "markdown": {"content": "你", "reasoning_content": null}}

event: end
data: {}
```



### 附录：变量说明

| 变量名     | 说明                             | 来源                                         |
| :--------- | :------------------------------- | :------------------------------------------- |
| agent_id   | 智能体 ID                        | 这里从agent接口中获取（runtime_template_id） |
| project_id | 项目 ID，通常为 runtime_agent_id | 这里从agent接口中获取(runtime_agent_id)      |
| agent_name | 智能体名称                       | 从 runtime 接口获取( agent_url_prefix)       |
| chat_id    | 会话 ID                          | 创建会话接口返回                             |
| base_url   | 运行时接口获取                   | 从 runtime 接口获取( url)                    |

------

如需进一步支持，请联系技术支持团队。


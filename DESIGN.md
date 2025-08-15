# 开源Agent运行时，langchain/langgraph - 增强设计

## 目标
基于langchain/langgraph实现灵活、可扩展的Agent运行时系统，接口符合ai-platform-backend的接口定义。采用混合架构设计，结合代码驱动的模板系统和API驱动的管理机制。

## 核心架构

### DDD分层架构设计
本项目采用严格的领域驱动设计(DDD)分层架构，确保清晰的关注点分离：

1. **领域层(Domain)**：核心业务逻辑和规则，无外部依赖
2. **应用层(Application)**：用例编排，命令查询职责分离(CQRS)
3. **基础设施层(Infrastructure)**：外部集成、Web API、数据持久化和框架实现

### 关键设计模式
- **CQRS模式**：分离读写操作，提高系统性能和可维护性
- **仓储模式**：将业务逻辑与数据访问解耦
- **工作单元模式**：管理原子事务边界
- **依赖注入**：通过接口解耦组件
- **策略模式**：通过插件支持多种AI框架

### 模板管理
结合代码驱动的模板发现机制和API驱动的模板管理：

1. **框架插件化模板发现**：通过扫描`runtime/infrastructure/frameworks`目录自动发现框架和模板
2. **API驱动的模板同步**：与平台后端同步模板元数据和配置
3. **动态模板注册**：支持运行时动态加载和卸载模板
4. **版本化模板管理**：支持多版本模板并存和兼容性检查

### 系统能力

#### 1. 领域层组件 (Domain Layer)
- **实体(Entities)**：
  - Agent实体：包含身份标识、配置和生命周期管理
  - Template实体：模板定义、元数据和验证规则
  - ExecutionSession实体：Agent执行会话和对话历史

- **值对象(Value Objects)**：
  - AgentId：唯一Agent标识符
  - ChatMessage：不可变消息对象，包含角色、内容和元数据
  - AgentConfiguration：配置设置和参数

- **领域服务(Domain Services)**：
  - AgentValidationService：复杂的Agent配置验证逻辑
  - TemplateDiscoveryService：模板发现和注册

#### 2. 应用层组件 (Application Layer)
- **命令(Commands)**：写操作，遵循CQRS模式
  - CreateAgentCommand：创建新Agent实例
  - UpdateAgentCommand：更新Agent配置
  - DeleteAgentCommand：删除Agent
  - ExecuteAgentCommand：执行Agent并处理消息

- **查询(Queries)**：读操作，遵循CQRS模式
  - GetAgentQuery：通过ID检索Agent
  - ListAgentsQuery：带过滤条件的Agent列表
  - GetSchemaQuery：获取运行时schema信息

- **应用服务(Application Services)**：用例编排
  - CreateAgentService：编排Agent创建用例
  - ExecuteAgentService：管理Agent执行管道
  - QueryAgentService：处理Agent查询和列表

#### 3. 基础设施层组件 (Infrastructure Layer)
- **Web API层(FastAPI)**：
  - Agent路由：Agent管理的CRUD操作
  - Execution路由：OpenAI兼容的聊天完成API
  - Schema路由：运行时schema和健康检查端点

- **框架集成**：插件化架构支持多种AI框架
  - LangGraph：基于状态的工作流执行
  - CrewAI：多Agent协作（计划中）
  - AutoGen：对话Agent（计划中）

- **模板发现机制**：
  - 系统启动时自动扫描`runtime/infrastructure/frameworks`目录
  - 每个框架提供独立的模板实现，遵循标准化接口
  - 支持热重载和动态注册新模板
  
- **Agent即模板设计**：
  ```python
  class BaseAgentTemplate(ABC):
      # 模板元数据（类变量）
      template_name: str = "Base Agent Template"
      template_id: str = "base-agent"
      template_version: str = "1.0.0"
      agent_type: AgentType = AgentType.CONVERSATION
      config_schema: Dict[str, Any] = {}
      
      # 模板级操作（类方法）
      @classmethod
      def get_metadata(cls) -> TemplateMetadata
      @classmethod
      def validate_config(cls, config: Dict[str, Any]) -> ValidationResult
      @classmethod
      def create_instance(cls, agent_data: AgentCreateRequest) -> 'BaseAgentTemplate'
      
      # 执行方法（实例方法）
      @abstractmethod
      async def execute(self, messages, stream=False, ...) -> ChatCompletionResponse
  ```

- **模板版本管理**：
  - 支持语义化版本控制（semver）
  - 版本兼容性检查和迁移
  - 多版本并存机制

#### 2. Agent管理模块 (Agent Management)  
- **Agent生命周期管理**：
  - 创建：基于模板+配置实例化Agent
  - 更新：支持配置热更新和模板版本升级
  - 删除：优雅关闭和资源清理
  - 状态管理：草稿 → 待审核 → 已发布工作流

- **Agent执行引擎**：
  - 基于LangGraph的状态管理和工作流执行
  - 支持流式响应和实时交互
  - 内置错误处理和重试机制
  - 执行监控和性能指标收集

#### 3. Agent调度模块 (Agent Scheduling)
- **动态调度**：按需创建和销毁Agent实例
- **资源管理**：连接池、内存管理、并发控制
- **负载均衡**：多实例负载分发（未来扩展）
- **监控告警**：实时监控Agent健康状态

## 目录结构

```
langchain-runtime/
├── runtime/                    # 运行时核心
│   ├── domain/                 # 领域层 - 核心业务逻辑
│   │   ├── entities/           # 富领域对象，具有唯一标识
│   │   │   ├── agent.py        # Agent实体
│   │   │   └── template.py     # Template实体
│   │   ├── value_objects/      # 不可变领域概念
│   │   │   ├── agent_id.py     # Agent标识符
│   │   │   ├── chat_message.py # 聊天消息
│   │   │   └── agent_configuration.py # Agent配置
│   │   ├── repositories/       # 仓储接口（契约）
│   │   │   ├── agent_repository.py  # Agent仓储接口
│   │   │   └── template_repository.py # Template仓储接口
│   │   ├── services/           # 复杂业务逻辑的领域服务
│   │   │   └── agent_validation_service.py # Agent验证服务
│   │   ├── events/             # 领域事件，用于解耦
│   │   └── unit_of_work/       # 事务边界接口
│   │
│   ├── application/            # 应用层 - 用例编排
│   │   ├── commands/           # 写操作（CQRS）
│   │   │   ├── create_agent_command.py   # 创建Agent命令
│   │   │   ├── execute_agent_command.py  # 执行Agent命令
│   │   │   └── delete_agent_command.py   # 删除Agent命令
│   │   ├── queries/            # 读操作（CQRS）
│   │   │   ├── get_agent_query.py    # 获取Agent查询
│   │   │   └── list_agents_query.py  # 列表Agent查询
│   │   └── services/           # 应用服务（编排）
│   │       ├── create_agent_service.py   # Agent创建服务
│   │       ├── execute_agent_service.py  # Agent执行服务
│   │       └── query_agent_service.py    # Agent查询服务
│   │
│   ├── infrastructure/         # 基础设施层 - 外部关注点
│   │   ├── web/                # Web API层（FastAPI）
│   │   │   ├── routes/         # API端点
│   │   │   │   ├── agent_routes.py      # Agent管理路由
│   │   │   │   └── execution_routes.py  # 执行路由
│   │   │   ├── models/         # 请求/响应DTO
│   │   │   │   ├── requests.py          # 请求模型
│   │   │   │   └── responses.py         # 响应模型
│   │   │   ├── dependencies.py # 依赖注入设置
│   │   │   └── main.py         # Web应用工厂
│   │   ├── repositories/       # 具体仓储实现
│   │   │   ├── memory_agent_repository.py    # 内存Agent仓储
│   │   │   └── memory_template_repository.py # 内存Template仓储
│   │   ├── unit_of_work/       # 具体UoW实现
│   │   │   └── memory_unit_of_work.py        # 内存工作单元
│   │   └── frameworks/         # AI框架集成（插件系统）
│   │       ├── langgraph/      # LangGraph框架实现
│   │       │   ├── executor.py # LangGraph执行器
│   │       │   ├── templates/  # LangGraph特定模板
│   │       │   │   ├── base.py         # LangGraph基础模板
│   │       │   │   ├── conversation.py # 对话模板
│   │       │   │   ├── simple.py       # 简单测试模板
│   │       │   │   └── workflow.py     # 工作流模板
│   │       │   └── utils/      # LangGraph工具
│   │       ├── crewai/         # CrewAI框架实现（计划中）
│   │       └── autogen/        # AutoGen框架实现（计划中）
│   │
│   ├── templates/              # 框架无关的模板定义
│   │   └── base.py             # 基础模板接口
│   │
│   ├── utils/                  # 共享工具
│   ├── config.py               # 配置管理
│   ├── auth.py                 # 认证
│   └── main.py                 # 应用入口点
│
├── tests/                      # 测试套件
├── docs/                       # 文档
├── examples/                   # 使用示例
└── pyproject.toml              # 项目配置
```

## 详细设计

### 1. 领域层设计

#### 核心实体
```python
# runtime/domain/entities/agent.py
class Agent:
    """Agent核心实体，包含身份标识和业务逻辑"""
    
    def __init__(
        self,
        agent_id: AgentId,
        name: str,
        template_id: str,
        configuration: dict,
        status: AgentStatus = AgentStatus.DRAFT
    ):
        self.id = agent_id
        self.name = name
        self.template_id = template_id
        self.configuration = configuration
        self.status = status
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
    
    def update_configuration(self, new_config: dict) -> None:
        """更新Agent配置，包含业务规则验证"""
        # 业务规则：只有草稿状态的Agent才能更新配置
        if self.status != AgentStatus.DRAFT:
            raise AgentConfigurationError("只有草稿状态的Agent才能更新配置")
        
        self.configuration = new_config
        self.updated_at = datetime.now(UTC)
```

#### 值对象
```python
# runtime/domain/value_objects/chat_message.py
class ChatMessage:
    """不可变的聊天消息值对象"""
    
    def __init__(
        self,
        role: MessageRole,
        content: str,
        timestamp: datetime = None,
        metadata: dict = None
    ):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(UTC)
        self.metadata = metadata or {}
    
    def __eq__(self, other):
        return (isinstance(other, ChatMessage) and
                self.role == other.role and
                self.content == other.content)
```

### 2. 应用层设计 - CQRS模式

#### 命令处理
```python
# runtime/application/services/create_agent_service.py
class CreateAgentService:
    """Agent创建应用服务，编排完整的创建用例"""
    
    def __init__(self, uow: UnitOfWorkInterface):
        self.uow = uow
    
    async def execute(self, command: CreateAgentCommand) -> Agent:
        """执行Agent创建用例"""
        async with self.uow:
            # 1. 验证模板存在
            template = await self.uow.templates.get_by_id(command.template_id)
            if not template:
                raise TemplateNotFoundError(f"模板 {command.template_id} 不存在")
            
            # 2. 创建Agent实体
            agent_id = AgentId.generate()
            agent = Agent(
                agent_id=agent_id,
                name=command.name,
                template_id=command.template_id,
                configuration=command.configuration
            )
            
            # 3. 领域验证
            validation_service = AgentValidationService()
            validation_result = await validation_service.validate(agent, template)
            if not validation_result.is_valid:
                raise AgentValidationError(validation_result.errors)
            
            # 4. 持久化
            await self.uow.agents.add(agent)
            await self.uow.commit()
            
            return agent
```

#### 查询处理
```python
# runtime/application/services/query_agent_service.py
class QueryAgentService:
    """Agent查询应用服务"""
    
    def __init__(self, agent_repository: AgentRepositoryInterface):
        self.agent_repository = agent_repository
    
    async def get_agent(self, query: GetAgentQuery) -> Optional[Agent]:
        """获取单个Agent"""
        return await self.agent_repository.get_by_id(query.agent_id)
    
    async def list_agents(self, query: ListAgentsQuery) -> List[Agent]:
        """获取Agent列表"""
        return await self.agent_repository.list(
            template_id=query.template_id,
            active_only=query.active_only,
            limit=query.limit,
            offset=query.offset
        )
```

### 3. 基础设施层设计 - 框架插件化

#### 框架执行器接口
```python
# runtime/infrastructure/frameworks/executor_base.py
class FrameworkExecutor(ABC):
    """框架执行器基类，定义框架集成规范"""
    
    framework_name: str
    supported_templates: List[str]
    
    @abstractmethod
    async def create_agent_instance(
        self, 
        agent: Agent, 
        template_class: type
    ) -> object:
        """创建框架特定的Agent实例"""
        pass
        
    @abstractmethod
    async def execute_agent(
        self,
        agent_instance: object,
        messages: List[ChatMessage],
        **kwargs
    ) -> ExecutionResult:
        """执行Agent的框架特定逻辑"""
        pass
```

#### LangGraph框架实现
```python
# runtime/infrastructure/frameworks/langgraph/executor.py
class LangGraphExecutor(FrameworkExecutor):
    """LangGraph框架执行器实现"""
    
    framework_name: str = "langgraph"
    supported_templates: List[str] = [
        "customer-service-bot",
        "langgraph-simple-test"
    ]
    
    async def create_agent_instance(
        self, 
        agent: Agent, 
        template_class: type
    ) -> BaseLangGraphAgent:
        """创建LangGraph Agent实例"""
        # 使用Agent配置创建请求对象
        request = CreateAgentRequest(
            id=agent.id.value,
            name=agent.name,
            template_id=agent.template_id,
            **agent.configuration
        )
        
        # 实例化模板
        return template_class(request)
    
    async def execute_agent(
        self,
        agent_instance: BaseLangGraphAgent,
        messages: List[ChatMessage],
        **kwargs
    ) -> ExecutionResult:
        """执行LangGraph Agent"""
        try:
            # 调用Agent的execute方法
            response = await agent_instance.execute(
                messages=messages,
                temperature=kwargs.get('temperature'),
                max_tokens=kwargs.get('max_tokens'),
                metadata=kwargs.get('metadata')
            )
            
            return ExecutionResult(
                success=True,
                response=response,
                metadata={"framework": "langgraph"}
            )
            
        except Exception as e:
            logger.error(f"LangGraph执行失败: {e}")
            raise FrameworkExecutionError(f"LangGraph执行错误: {str(e)}")
```

### 4. 模板系统设计

#### 框架无关的模板接口
```python
# runtime/templates/base.py
class BaseAgentTemplate(ABC):
    """所有Agent模板的基类，框架无关"""
    
    # 模板元数据
    template_name: str = "Base Agent Template"
    template_id: str = "base-agent"
    template_version: str = "1.0.0"
    template_description: str = "基础Agent模板"
    framework: str = "base"

    def __init__(
        self, 
        agent_data: CreateAgentRequest, 
        llm_service=None, 
        toolset_service=None
    ) -> None:
        # 解析请求为结构化模型，更好地分离关注点
        identity = agent_data.get_identity()
        template = agent_data.get_template()
        config = agent_data.get_agent_configuration()
        
        # 初始化身份和模板字段
        self.id = identity.id
        self.name = identity.name
        self.template_id = template.template_id
        self.template_version = template.get_template_version() or self.template_version
        self.template_config = config.config or {}
        
        # 服务依赖
        self.llm_service = llm_service
        self.toolset_service = toolset_service

    @abstractmethod
    async def execute(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """执行Agent，必须由子类实现"""
        pass

    @abstractmethod
    async def stream_execute(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """流式执行Agent，必须由子类实现"""
        pass
```

#### LangGraph框架特定实现
```python
# runtime/infrastructure/frameworks/langgraph/templates/conversation.py
class ConversationAgent(BaseLangGraphAgent):
    template_name: str = "智能客服助手"
    template_id: str = "customer-service-bot"
    template_version: str = "1.0.0"
    template_description: str = "基于LangGraph的智能客服对话Agent"
    
    async def _build_graph(self) -> CompiledStateGraph:
        """构建LangGraph对话流程图"""
        # 创建状态图
        builder = StateGraph(ConversationState)
        
        # 添加节点
        builder.add_node("conversation", self._conversation_node)
        builder.add_node("response", self._response_node)
        
        # 设置入口点
        builder.set_entry_point("conversation")
        
        # 添加边
        builder.add_edge("conversation", "response")
        builder.add_edge("response", END)
        
        # 编译并返回
        return builder.compile()
    
    async def execute(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """执行对话Agent"""
        graph = await self.graph
        
        # 构建初始状态
        initial_state = ConversationState(
            messages=messages,
            temperature=temperature or 0.7,
            max_tokens=max_tokens or 1000,
            metadata=metadata or {}
        )
        
        # 执行图
        result = await graph.ainvoke(initial_state)
        
        # 转换为标准响应格式
        return self._convert_to_chat_completion_response(result)
```

## 集成点设计

### 1. 与平台后端的集成
- **模板同步**：后端向运行时请求模板数据
- **Agent状态同步**：Agent创建/更新/删除时同步状态
- **监控数据上报**：定期上报运行状态和指标数据

### 2. 与LLM代理的集成  
- **统一LLM客户端**：抽象LLM调用接口，支持多种模型
- **连接池管理**：复用连接，提高性能
- **降级策略**：LLM服务不可用时的降级处理

### 3. OpenAI兼容接口
- **Chat Completions API**：完全兼容OpenAI接口规范
- **流式响应**：支持Server-Sent Events流式输出  
- **错误处理**：标准化错误响应格式

## 实施计划

### ✅ 第一阶段：DDD分层架构（已完成）
1. ✅ 实现完整的DDD分层结构（Domain/Application/Infrastructure）
2. ✅ 建立CQRS命令查询职责分离模式
3. ✅ 实现仓储模式和工作单元模式
4. ✅ 建立依赖注入和Web API层

### ✅ 第二阶段：框架插件化系统（已完成）
1. ✅ 创建框架执行器基础接口
2. ✅ 实现LangGraph框架集成
3. ✅ 建立模板发现和注册机制
4. ✅ 实现基础对话和简单测试模板

### 🔄 第三阶段：模板系统扩展（进行中）
1. [ ] 实现TaskAgent模板（任务执行Agent）
2. [ ] 实现CustomAgent模板（自定义代码Agent）
3. [ ] 添加更多框架支持（CrewAI、AutoGen）
4. [ ] 完善模板配置验证

### 📋 第四阶段：API完善（计划中）
1. [ ] 完善Agent CRUD API（添加PUT/DELETE端点）
2. [ ] 增强错误处理和验证
3. [ ] 完善OpenAI兼容性
4. [ ] 添加API文档和示例

### 🚀 第五阶段：性能优化（未来）
1. [ ] 实现连接池和资源管理
2. [ ] 添加缓存层
3. [ ] 优化并发执行
4. [ ] 添加监控和指标收集

## 技术优势

1. **严格分层架构**：DDD分层设计确保清晰的关注点分离和代码可维护性
2. **CQRS模式**：命令查询职责分离提高系统性能和可扩展性
3. **插件化框架**：支持多种AI框架的插件化集成，易于扩展
4. **类型安全**：全面的类型注解和Pydantic验证确保代码质量
5. **异步高性能**：基于asyncio的高性能异步设计
6. **OpenAI兼容**：完全兼容OpenAI API规范，易于集成
7. **可观测性**：内置监控、日志和健康检查
8. **测试友好**：依赖注入和仓储模式使单元测试更容易

## 扩展能力

### 未来扩展方向
1. **模板市场**：支持模板分享和下载
2. **分布式部署**：多实例负载均衡和容错
3. **插件系统**：支持第三方工具和服务集成
4. **可视化工作流**：图形化编辑复杂Agent流程
5. **A/B测试**：支持多版本Agent并行测试

这种基于DDD的分层架构设计结合插件化框架系统，既保持了模板系统的灵活性和可扩展性，又确保了企业级的代码质量和可维护性，为AI Agent运行时系统的未来发展奠定了坚实的架构基础。

## 框架开发指南

本章节专为运行时开发者提供，指导如何集成新的AI框架或扩展现有框架。

### 添加新框架的步骤

#### 第一步：创建框架目录结构

```
runtime/infrastructure/frameworks/your_framework/
├── __init__.py
├── executor.py              # 框架执行器实现
├── templates/               # 框架特定模板
│   ├── __init__.py
│   ├── base.py             # 框架基础模板
│   ├── conversation.py     # 对话模板实现
│   └── task.py             # 任务模板实现
└── utils/                  # 框架工具
    ├── __init__.py
    └── client.py           # 框架客户端包装器
```

#### 第二步：实现框架执行器

```python
# runtime/infrastructure/frameworks/your_framework/executor.py
from runtime.infrastructure.frameworks.executor_base import FrameworkExecutor
from runtime.domain.entities.agent import Agent
from runtime.domain.value_objects.chat_message import ChatMessage

class YourFrameworkExecutor(FrameworkExecutor):
    """你的框架执行器实现"""
    
    framework_name: str = "your_framework"
    supported_templates: List[str] = [
        "conversation-agent",
        "task-agent"
    ]
    
    def __init__(self, config: dict):
        self.config = config
        # 初始化框架特定客户端
        
    async def create_agent_instance(
        self, 
        agent: Agent, 
        template_class: type
    ) -> object:
        """创建框架特定的Agent实例"""
        # 实现Agent实例化逻辑
        pass
        
    async def execute_agent(
        self,
        agent_instance: object,
        messages: List[ChatMessage],
        **kwargs
    ) -> ExecutionResult:
        """执行Agent的框架特定逻辑"""
        # 实现执行逻辑
        pass
        
    async def validate_template_config(
        self, 
        template_id: str, 
        config: dict
    ) -> ValidationResult:
        """验证此框架的模板配置"""
        # 实现验证逻辑
        pass
```

#### 第三步：创建框架基础模板

```python
# runtime/infrastructure/frameworks/your_framework/templates/base.py
from runtime.templates.base import BaseAgentTemplate
from runtime.infrastructure.web.models.requests import CreateAgentRequest

class BaseYourFrameworkAgent(BaseAgentTemplate):
    """你的框架Agent模板基类"""
    
    framework: str = "your_framework"
    
    def __init__(
        self, 
        agent_data: CreateAgentRequest, 
        llm_service=None, 
        toolset_service=None
    ):
        super().__init__(agent_data, llm_service, toolset_service)
        # 框架特定初始化
        
    async def _initialize_framework_client(self):
        """初始化框架特定客户端"""
        # 实现框架客户端初始化
        pass
        
    @abstractmethod
    async def _build_framework_agent(self):
        """构建框架特定Agent结构"""
        pass
```

#### 第四步：实现模板类型

```python
# runtime/infrastructure/frameworks/your_framework/templates/conversation.py
class YourFrameworkConversationAgent(BaseYourFrameworkAgent):
    template_name: str = "对话Agent"
    template_id: str = "your-framework-conversation"
    template_version: str = "1.0.0"
    template_description: str = "使用你的框架的对话Agent"
    
    async def execute(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        """使用你的框架执行对话"""
        # 实现框架特定对话逻辑
        pass
        
    async def stream_execute(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """使用你的框架流式对话"""
        # 实现框架特定流式逻辑
        pass
```

#### 第五步：注册框架模板

```python
# runtime/infrastructure/frameworks/your_framework/templates/__init__.py
from .conversation import YourFrameworkConversationAgent
from .task import YourFrameworkTaskAgent

# 此框架的模板注册表
_TEMPLATE_CLASSES = {
    "your-framework-conversation": YourFrameworkConversationAgent,
    "your-framework-task": YourFrameworkTaskAgent,
}

def get_your_framework_templates() -> List[dict]:
    """获取可用的你的框架模板列表及元数据"""
    templates = []
    
    for template_id, template_class in _TEMPLATE_CLASSES.items():
        metadata = {
            "template_id": template_id,
            "template_name": getattr(template_class, 'template_name', template_id),
            "template_version": getattr(template_class, 'template_version', '1.0.0'),
            "description": getattr(template_class, 'template_description', ''),
            "framework": "your_framework",
            "class": template_class,
        }
        templates.append(metadata)
    
    return templates

def get_your_framework_template_classes() -> dict[str, type]:
    """获取模板ID到模板类的映射"""
    return _TEMPLATE_CLASSES.copy()
```

### 框架开发最佳实践

#### 1. 错误处理
```python
class YourFrameworkError(Exception):
    """你的框架操作基础异常"""
    pass

class YourFrameworkExecutionError(YourFrameworkError):
    """Agent执行失败时抛出"""
    pass

class YourFrameworkConfigurationError(YourFrameworkError):
    """配置无效时抛出"""
    pass
```

#### 2. 日志和监控
```python
import logging

logger = logging.getLogger(__name__)

class YourFrameworkExecutor(FrameworkExecutor):
    async def execute_agent(self, agent_instance, messages, **kwargs):
        logger.info(f"执行Agent {agent_instance.id}，消息数量：{len(messages)}")
        
        try:
            result = await self._execute_internal(agent_instance, messages, **kwargs)
            logger.info(f"Agent执行成功完成")
            return result
        except Exception as e:
            logger.error(f"Agent执行失败：{e}")
            raise
```

#### 3. 配置验证
```python
from pydantic import BaseModel, Field

class YourFrameworkConfig(BaseModel):
    api_key: str = Field(..., description="你的框架API密钥")
    timeout: int = Field(30, description="请求超时时间（秒）")
    max_retries: int = Field(3, description="最大重试次数")
    
    class Config:
        extra = "forbid"
```

### 必需的模板类型

每个框架都应该实现这些核心模板类型：

1. **对话Agent**：通用对话型智能体
2. **任务Agent**：结构化任务执行，包含步骤
3. **自定义Agent**：具有自定义行为的灵活Agent

### 集成检查清单

- [ ] 框架执行器实现了所有必需方法
- [ ] 创建了框架基础模板类
- [ ] 实现了所有必需的模板类型
- [ ] 框架已在发现系统中注册
- [ ] 实现了配置验证
- [ ] 添加了错误处理和日志
- [ ] 编写了单元测试
- [ ] 更新了文档

### API兼容性

确保你的框架保持与以下内容的兼容性：

- OpenAI Chat Completions API格式
- 流式响应格式（Server-Sent Events）
- 标准错误响应格式
- 认证和授权

### 性能考虑

- 对外部API调用使用连接池
- 实现正确的async/await模式
- 在可能的情况下缓存框架客户端
- 优雅处理速率限制
- 监控长时间运行Agent的内存使用

此框架开发指南确保了一致的集成模式，并维护Agent运行时系统的高质量和可靠性。


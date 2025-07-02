# 开源Agent运行时，langchain/langgraph - 增强设计

## 目标
基于langchain/langgraph实现灵活、可扩展的Agent运行时系统，接口符合ai-platform-backend的接口定义。采用混合架构设计，结合代码驱动的模板系统和API驱动的管理机制。

## 核心架构

### 模板管理
结合代码驱动的模板发现机制和API驱动的模板管理：

1. **代码驱动的模板发现**：通过扫描`template_agent`目录自动发现和加载模板
2. **API驱动的模板同步**：与平台后端同步模板元数据和配置
3. **动态模板注册**：支持运行时动态加载和卸载模板
4. **版本化模板管理**：支持多版本模板并存和兼容性检查

### 系统能力

#### 1. 模板管理模块 (Template Management)
- **模板发现机制**：
  - 系统启动时自动扫描`runtime/template_agent`目录
  - 每个模板是独立的Python模块，提供标准化接口
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
├── runtime/
│   ├── template_agent/          # 模板代码目录
│   │   ├── __init__.py
│   │   ├── base.py             # 基础模板接口
│   │   ├── discovery.py        # 模板发现机制
│   │   ├── conversation/       # 对话型模板
│   │   │   ├── __init__.py
│   │   │   └── template.py
│   │   ├── task/              # 任务型模板
│   │   │   ├── __init__.py
│   │   │   └── template.py
│   │   └── custom/            # 自定义模板
│   │       ├── __init__.py
│   │       └── template.py
│   ├── core/                   # 核心业务逻辑
│   │   ├── template_manager.py # 模板管理器
│   │   ├── agent_factory.py   # Agent工厂
│   │   └── scheduler.py       # 调度器
│   ├── agents.py              # Agent基类和实现
│   ├── api.py                 # FastAPI路由
│   ├── models.py              # Pydantic模型
│   ├── schema.py              # 动态schema生成
│   └── main.py                # 应用入口
```

## 详细设计

### 1. 基于类继承的模板发现

```python
# runtime/template_agent/base.py
def get_all_agent_templates() -> List[Type[BaseAgentTemplate]]:
    """使用Python类继承机制发现所有Agent模板"""
    def get_subclasses(cls):
        subclasses = set(cls.__subclasses__())
        for subclass in list(subclasses):
            subclasses.update(get_subclasses(subclass))
        return subclasses
    
    return list(get_subclasses(BaseAgentTemplate))

def get_template_by_id(template_id: str) -> Optional[Type[BaseAgentTemplate]]:
    """通过模板ID获取Agent模板类"""
    for template_class in get_all_agent_templates():
        if template_class.template_id == template_id:
            return template_class
    return None
```

### 2. 模板管理器

```python
# runtime/core/template_manager.py
class TemplateManager:
    def __init__(self):
        self.discovery = TemplateDiscovery(TEMPLATE_DIR)
        self.templates = {}
        self.version_map = defaultdict(list)
        self.load_all_templates()
    
    def load_all_templates(self) -> None:
        """加载所有发现的模板"""
        discovered = self.discovery.scan_templates()
        for template in discovered:
            self.register_template(template)
    
    def get_template(self, template_id: str, version: str = None) -> BaseTemplate:
        """获取指定模板，支持版本选择"""
        if version:
            return self.templates.get(f"{template_id}:{version}")
        
        # 返回最新版本
        versions = self.version_map.get(template_id, [])
        if versions:
            latest_version = max(versions, key=lambda v: semver.VersionInfo.parse(v))
            return self.templates.get(f"{template_id}:{latest_version}")
        return None
    
    def get_schema(self) -> SchemaResponse:
        """生成运行时schema，包含所有模板信息"""
        agent_templates = []
        for template in self.templates.values():
            metadata = template.get_metadata()
            agent_templates.append(AgentTemplate(
                template_name=metadata.name,
                template_id=metadata.template_id,
                version=metadata.version,
                configSchema=metadata.config_schema,
                runtimeRequirements=metadata.runtime_requirements
            ))
        
        return SchemaResponse(
            version=__version__,
            lastUpdated=datetime.now().isoformat(),
            supportedAgentTemplates=agent_templates,
            capabilities=self._get_capabilities(),
            limits=self._get_limits()
        )
```

### 3. 简化的Agent创建

```python
# runtime/template_agent/manager.py
class TemplateManager:
    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """直接通过模板类创建Agent实例"""
        template_class = self.get_template_class(
            agent_data.template_id,
            agent_data.template_version_id
        )
        
        if not template_class:
            raise ValueError(f"Template {agent_data.template_id} not found")
        
        # 使用类方法创建实例（内置验证）
        return template_class.create_instance(agent_data)
    
    def get_template_class(self, template_id: str, version: str = None) -> Type[BaseAgentTemplate]:
        """获取模板类"""
        if version:
            return self.templates.get(f"{template_id}:{version}")
        
        # 返回最新版本
        versions = self.version_map.get(template_id, [])
        if versions:
            latest_version = versions[0]
            return self.templates.get(f"{template_id}:{latest_version}")
        return None
```

### 4. Agent模板实现示例

- FreeStyle Agent
```python
# runtime/template_agent/free_style.py
class FreeStyleAgent(BaseAgentTemplate):
    """灵活Agent模板，使用ReAct模式自由组合工具，执行特定的任务"""
    
    # 模板元数据（类变量）
    template_name: str = "自由的代理"
    template_id: str = "free-style"
    template_version: str = "1.0.0"
    template_description: str = "灵活对话型智能体，适用于通用的简单任务"
    agent_type: AgentType = AgentType.FREESTYLE
    
    # 配置模式（类变量）
    config_schema: Dict[str, Any] = {
        "context": {
            "type": "string",
            "default": "",
            "description": "智能体执行上下文，限制智能体的工作范围",
            "order": 0
        },
        "task_buget": {
            "type": "integer",
            "default": 20,
            "minimum": 3,
            "maximum": 100,
            "description": "每次任务最大工具调用次数",
            "order": 1
        }
    }
    
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> ValidationResult:
        """增强的配置验证（类方法）"""
        result = super().validate_config(config)
        # 添加特定验证逻辑
        return result
    
    def _build_graph(self) -> StateGraph:
        """构建对话流程图（实例方法）"""
        # 实现LangGraph工作流
        pass
    
    async def execute(self, messages, stream=False, ...) -> ChatCompletionResponse:
        """执行对话（实例方法）"""
        # 实现对话执行逻辑
        pass
```

- RunBook Agent
```python
# runtime/template_agent/runbook.py
class RunbookAgent(BaseAgentTemplate):
    """逐步执行任务的Agent，根据配置的任务执行步骤执行，完成给定的任务"""
    
    # 模板元数据（类变量）
    template_name: str = "逐步执行任务代理"
    template_id: str = "runbook"
    template_version: str = "1.0.0"
    template_description: str = "逐步执行任务，适用于固定的任务流程执行，但支持一定的自主性，由Agent决定每一步是否完成"
    agent_type: AgentType = AgentType.RUNBOOK
    
    # 配置模式（类变量）
    config_schema: Dict[str, Any] = {
        "context": {
            "type": "string",
            "default": "",
            "description": "智能体执行上下文，限制智能体的工作范围",
            "order": 0
        },
        "task_buget": {
            "type": "integer",
            "default": 20,
            "minimum": 3,
            "maximum": 100,
            "description": "每次任务最大工具调用次数",
            "order": 1
        }
    }
    
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> ValidationResult:
        """增强的配置验证（类方法）"""
        result = super().validate_config(config)
        # 添加特定验证逻辑
        return result
    
    def _build_graph(self) -> StateGraph:
        """构建对话流程图（实例方法）"""
        # 实现LangGraph工作流
        pass
    
    async def execute(self, messages, stream=False, ...) -> ChatCompletionResponse:
        """执行对话（实例方法）"""
        # 实现对话执行逻辑
        pass
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

### 第一阶段：核心架构
1. 实现`BaseTemplate`接口和模板发现机制
2. 创建`TemplateManager`和`AgentFactory`
3. 迁移现有Agent类型到模板模块
4. 实现动态schema生成

### 第二阶段：模板系统
1. 实现两种基础模板（freetyle, workflow）
2. 添加模板版本管理和兼容性检查
3. 实现配置验证和错误处理
4. 添加模板热重载功能

### 第三阶段：集成优化
1. 完善与平台后端的集成
2. 优化性能和资源管理
3. 添加监控和日志
4. 完善文档和测试

## 技术优势

1. **模块化设计**：代码驱动的模板系统，易于扩展
2. **向后兼容**：现有API接口保持不变  
3. **类型安全**：全面的类型注解和Pydantic验证
4. **高性能**：基于asyncio和连接池的高性能设计
5. **可观测性**：内置监控、日志和健康检查
6. **标准化**：符合OpenAI接口规范，易于集成

## 扩展能力

### 未来扩展方向
1. **模板市场**：支持模板分享和下载
2. **分布式部署**：多实例负载均衡和容错
3. **插件系统**：支持第三方工具和服务集成
4. **可视化工作流**：图形化编辑复杂Agent流程
5. **A/B测试**：支持多版本Agent并行测试

这种混合架构设计既保持了代码驱动模板系统的灵活性和可扩展性，又充分利用了现有实现的稳定性和性能优势，为未来的功能扩展奠定了坚实基础。


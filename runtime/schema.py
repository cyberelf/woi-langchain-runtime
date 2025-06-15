"""Schema definitions for supported agent templates."""

from datetime import datetime
from typing import Dict, List

from .models import (
    AgentTemplate, AgentTemplateSchema, ConfigSection, ConfigField,
    FieldValidation, RuntimeRequirements, SchemaResponse,
    RuntimeCapabilities, RuntimeLimits
)
from .config import settings


def get_conversation_agent_template() -> AgentTemplate:
    """Get conversation agent template definition."""
    return AgentTemplate(
        template_name="智能客服助手",
        template_id="customer-service-bot",
        version="1.0.0",
        configSchema=AgentTemplateSchema(
            template_name="智能客服助手",
            template_id="customer-service-bot",
            sections=[
                ConfigSection(
                    id="conversation",
                    title="对话设置",
                    description="配置智能体的对话行为",
                    fields=[
                        ConfigField(
                            id="continuous",
                            type="checkbox",
                            label="持续对话模式",
                            description="启用持续对话以保持上下文连贯性",
                            defaultValue=True
                        ),
                        ConfigField(
                            id="historyLength",
                            type="number",
                            label="对话历史长度",
                            description="保留的最大历史消息数量",
                            defaultValue=10,
                            validation=FieldValidation(min=5, max=100)
                        )
                    ]
                )
            ]
        ),
        runtimeRequirements=RuntimeRequirements(
            memory="2GB",
            cpu="1 core",
            gpu=False,
            estimatedLatency="500ms"
        )
    )


def get_task_agent_template() -> AgentTemplate:
    """Get task agent template definition."""
    return AgentTemplate(
        template_name="任务型智能体",
        template_id="task-execution-bot",
        version="1.1.0",
        configSchema=AgentTemplateSchema(
            template_name="任务型智能体",
            template_id="task-execution-bot",
            sections=[
                ConfigSection(
                    id="taskSteps",
                    title="任务步骤",
                    description="配置任务执行的步骤和参数",
                    fields=[
                        ConfigField(
                            id="steps",
                            type="array",
                            label="执行步骤",
                            description="任务执行的步骤列表",
                            defaultValue=["分析需求", "制定计划", "执行任务", "验证结果"],
                            validation=FieldValidation(minItems=1, maxItems=20)
                        ),
                        ConfigField(
                            id="stepTimeout",
                            type="number",
                            label="步骤超时",
                            description="每个步骤的超时时间（秒）",
                            defaultValue=300,
                            validation=FieldValidation(min=10, max=3600)
                        ),
                        ConfigField(
                            id="retryCount",
                            type="number",
                            label="重试次数",
                            description="步骤失败时的重试次数",
                            defaultValue=2,
                            validation=FieldValidation(min=0, max=5)
                        ),
                        ConfigField(
                            id="parallelExecution",
                            type="checkbox",
                            label="并行执行",
                            description="是否允许步骤并行执行",
                            defaultValue=False
                        )
                    ]
                ),
                ConfigSection(
                    id="validation",
                    title="验证设置",
                    description="配置任务验证和输出格式",
                    fields=[
                        ConfigField(
                            id="strictMode",
                            type="checkbox",
                            label="严格模式",
                            description="是否启用严格验证模式",
                            defaultValue=True
                        ),
                        ConfigField(
                            id="outputFormat",
                            type="select",
                            label="输出格式",
                            description="任务输出的格式类型",
                            defaultValue="structured"
                        )
                    ]
                )
            ]
        ),
        runtimeRequirements=RuntimeRequirements(
            memory="4GB",
            cpu="2 cores",
            gpu=False,
            estimatedLatency="1000ms"
        )
    )


def get_custom_agent_template() -> AgentTemplate:
    """Get custom agent template definition."""
    return AgentTemplate(
        template_name="自定义智能体",
        template_id="custom-code-bot",
        version="1.0.0",
        configSchema=AgentTemplateSchema(
            template_name="自定义智能体",
            template_id="custom-code-bot",
            sections=[
                ConfigSection(
                    id="codeSource",
                    title="代码源",
                    description="配置自定义代码的来源和内容",
                    fields=[
                        ConfigField(
                            id="type",
                            type="select",
                            label="代码类型",
                            description="代码的来源类型",
                            defaultValue="inline"
                        ),
                        ConfigField(
                            id="content",
                            type="textarea",
                            label="代码内容",
                            description="内联代码或代码引用"
                        ),
                        ConfigField(
                            id="entryPoint",
                            type="text",
                            label="入口点",
                            description="代码执行的入口函数",
                            defaultValue="main"
                        ),
                        ConfigField(
                            id="dependencies",
                            type="array",
                            label="依赖包",
                            description="代码运行所需的依赖包列表",
                            defaultValue=[]
                        )
                    ]
                ),
                ConfigSection(
                    id="runtime",
                    title="运行时设置",
                    description="配置代码执行的运行时环境",
                    fields=[
                        ConfigField(
                            id="language",
                            type="select",
                            label="编程语言",
                            description="代码使用的编程语言",
                            defaultValue="python"
                        ),
                        ConfigField(
                            id="version",
                            type="text",
                            label="语言版本",
                            description="编程语言的版本号"
                        ),
                        ConfigField(
                            id="timeout",
                            type="number",
                            label="执行超时",
                            description="代码执行超时时间（秒）",
                            defaultValue=30,
                            validation=FieldValidation(min=1, max=300)
                        ),
                        ConfigField(
                            id="memoryLimit",
                            type="number",
                            label="内存限制",
                            description="内存限制（MB）",
                            defaultValue=512,
                            validation=FieldValidation(min=64, max=2048)
                        )
                    ]
                )
            ]
        ),
        runtimeRequirements=RuntimeRequirements(
            memory="1GB",
            cpu="1 core",
            gpu=False,
            estimatedLatency="2000ms"
        )
    )


def get_runtime_schema() -> SchemaResponse:
    """Get the complete runtime schema."""
    return SchemaResponse(
        version="1.2.0",
        lastUpdated=datetime.now().isoformat(),
        supportedAgentTemplates=[
            get_conversation_agent_template(),
            get_task_agent_template(),
            get_custom_agent_template()
        ],
        capabilities=RuntimeCapabilities(
            streaming=True,
            toolCalling=True,
            multimodal=False,
            codeExecution=True
        ),
        limits=RuntimeLimits(
            maxConcurrentAgents=settings.max_concurrent_agents,
            maxMessageLength=settings.max_message_length,
            maxConversationHistory=settings.max_conversation_history
        )
    ) 
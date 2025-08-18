# test the execution of an agent

import pytest
from runtime.application.services.execute_agent_service import ExecuteAgentServiceV2
from runtime.application.commands.execute_agent_command import ExecuteAgentCommand
from runtime.domain.entities.agent import Agent
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole
from runtime.core.agent_task_manager import AgentTaskManager, TaskStatus
from runtime.core.message_queue import InMemoryMessageQueue
from runtime.infrastructure.unit_of_work.in_memory_uow import TransactionalInMemoryUnitOfWork


@pytest.mark.asyncio
async def test_execute_agent():
    """Test agent execution with proper task manager initialization."""
    # Setup message queue and unit of work
    message_queue = InMemoryMessageQueue()
    uow = TransactionalInMemoryUnitOfWork()
    
    # Create a test agent
    agent = Agent.create(
        name="test-agent", 
        template_id="langgraph-simple-test",
        template_version="1.0.0",
        configuration={},
        metadata={}
    )
    
    # Store the agent in the unit of work
    await uow.agents.save(agent)
    await uow.commit()
    
    # Setup LangGraph framework executor (now works with graceful fallbacks)
    from runtime.infrastructure.frameworks.langgraph.executor import LangGraphFrameworkExecutor
    framework_executor = LangGraphFrameworkExecutor()
    
    # Create and initialize task manager
    task_manager = AgentTaskManager(
        message_queue=message_queue,
        uow=uow,
        max_workers=2,
        cleanup_interval_seconds=60,
        instance_timeout_seconds=120
    )
    
    # Initialize the task manager with framework
    await task_manager.initialize(framework_executor)
    
    try:
        # Create execute agent service
        service = ExecuteAgentServiceV2(task_manager)
        
        # Create execution command
        command = ExecuteAgentCommand(
            agent_id=str(agent.id),
            messages=[
                ChatMessage(
                    role=MessageRole.USER,
                    content="Hello, test message"
                )
            ],
            session_id="test-session",
            user_id="test-user",
            stream=False,
            temperature=0.7,
            max_tokens=100
        )
        
        # Execute the agent
        result = await service.execute(command)
        
        # Verify result
        assert result is not None
        assert result.agent_id == str(agent.id)
        assert result.status == TaskStatus.COMPLETED
        print(f"Execution result: {result.status}, message: {result.message}")
        
    finally:
        # Cleanup
        await task_manager.shutdown()
    
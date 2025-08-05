"""Execute agent application service - Use case implementation."""

import logging
from typing import List, Optional, AsyncGenerator, Any

from ...domain.entities.agent import Agent, AgentStatus
from ...domain.entities.chat_session import ChatSession
from ...domain.value_objects.session_id import SessionId
from ...domain.unit_of_work.unit_of_work import UnitOfWorkInterface
from ...domain.events.domain_events import SessionStarted, MessageAdded
from ..commands.execute_agent_command import ExecuteAgentCommand

logger = logging.getLogger(__name__)


class AgentExecutionResult:
    """Result of agent execution."""
    
    def __init__(self, session: ChatSession, response_content: str, metadata: dict = None):
        self.session = session
        self.response_content = response_content
        self.metadata = metadata or {}


class ExecuteAgentService:
    """Application service for executing agents.
    
    Orchestrates the agent execution use case. Manages session lifecycle,
    transaction boundaries, and coordinates with domain objects.
    """
    
    def __init__(self, uow: UnitOfWorkInterface, agent_runtime):
        self.uow = uow
        self.agent_runtime = agent_runtime  # Framework integration dependency
        self._events: List[object] = []
    
    async def execute(self, command: ExecuteAgentCommand) -> AgentExecutionResult:
        """Execute the agent execution use case.
        
        This method represents the complete business transaction for
        executing an agent and managing session state.
        """
        logger.info(f"Executing agent: {command.agent_id}")
        
        async with self.uow:
            try:
                # 1. Get agent from repository
                agent = await self.uow.agents.get_by_id(command.agent_id)
                if not agent:
                    raise ValueError(f"Agent {command.agent_id} not found")
                
                # 2. Validate agent is executable
                if not agent.is_active():
                    raise ValueError(f"Agent {command.agent_id} is not active")
                
                if not agent.is_configured_properly():
                    raise ValueError(f"Agent {command.agent_id} is not properly configured")
                
                # 3. Get or create session
                session = await self._get_or_create_session(command, agent)
                
                # 4. Add user messages to session
                for message in command.messages:
                    if message.is_user_message():
                        session.add_message(message)
                        
                        # Raise domain event
                        event = MessageAdded.create(
                            session_id=session.id,
                            message_role=message.role.value,
                            message_content=message.content
                        )
                        self._events.append(event)
                
                # 5. Execute agent through runtime (infrastructure concern)
                response_content = await self._execute_agent_runtime(
                    agent, session, command
                )
                
                # 6. Add assistant response to session
                from ...domain.value_objects.chat_message import ChatMessage
                assistant_message = ChatMessage.create_assistant_message(
                    content=response_content,
                    metadata=command.metadata or {}
                )
                session.add_message(assistant_message)
                
                # Raise domain event
                event = MessageAdded.create(
                    session_id=session.id,
                    message_role=assistant_message.role.value,
                    message_content=assistant_message.content
                )
                self._events.append(event)
                
                # 7. Save session
                await self.uow.sessions.save(session)
                
                # 8. Commit transaction
                await self.uow.commit()
                
                logger.info(f"Successfully executed agent: {command.agent_id}")
                return AgentExecutionResult(
                    session=session,
                    response_content=response_content,
                    metadata=command.metadata or {}
                )
                
            except Exception as e:
                logger.error(f"Failed to execute agent: {e}")
                await self.uow.rollback()
                raise
    
    async def execute_streaming(self, command: ExecuteAgentCommand) -> AsyncGenerator[str, None]:
        """Execute agent with streaming response.
        
        This is a specialized version for streaming use cases.
        """
        logger.info(f"Executing agent with streaming: {command.agent_id}")
        
        async with self.uow:
            try:
                # 1. Get agent and session (same as regular execute)
                agent = await self.uow.agents.get_by_id(command.agent_id)
                if not agent:
                    raise ValueError(f"Agent {command.agent_id} not found")
                
                session = await self._get_or_create_session(command, agent)
                
                # 2. Add user messages
                for message in command.messages:
                    if message.is_user_message():
                        session.add_message(message)
                
                # 3. Stream agent execution
                response_chunks = []
                async for chunk in self._execute_agent_runtime_streaming(
                    agent, session, command
                ):
                    response_chunks.append(chunk)
                    yield chunk
                
                # 4. Save complete response to session
                complete_response = "".join(response_chunks)
                from ...domain.value_objects.chat_message import ChatMessage
                assistant_message = ChatMessage.create_assistant_message(
                    content=complete_response,
                    metadata=command.metadata or {}
                )
                session.add_message(assistant_message)
                
                # 5. Save and commit
                await self.uow.sessions.save(session)
                await self.uow.commit()
                
            except Exception as e:
                logger.error(f"Failed to execute streaming agent: {e}")
                await self.uow.rollback()
                raise
    
    async def _get_or_create_session(
        self, command: ExecuteAgentCommand, agent: Agent
    ) -> ChatSession:
        """Get existing session or create new one."""
        
        # If session ID provided, try to get existing session
        if command.session_id:
            session = await self.uow.sessions.get_by_id(command.session_id)
            if session:
                session.touch()  # Update last activity
                return session
        
        # If user ID provided, try to get existing session for this agent/user
        if command.user_id:
            session = await self.uow.sessions.get_by_agent_and_user(
                agent.id, command.user_id
            )
            if session and not session.is_expired():
                session.touch()
                return session
        
        # Create new session
        session = ChatSession.create(
            agent_id=agent.id,
            user_id=command.user_id,
            metadata=command.metadata or {}
        )
        
        # Raise domain event
        event = SessionStarted.create(
            session_id=session.id,
            agent_id=agent.id,
            user_id=command.user_id or "anonymous"
        )
        self._events.append(event)
        
        return session
    
    async def _execute_agent_runtime(
        self, agent: Agent, session: ChatSession, command: ExecuteAgentCommand
    ) -> str:
        """Execute agent through runtime infrastructure.
        
        This delegates to infrastructure layer for actual execution.
        """
        # This would use the agent runtime to execute the agent
        # For now, return a placeholder
        return f"Response from agent {agent.name} for session {session.id}"
    
    async def _execute_agent_runtime_streaming(
        self, agent: Agent, session: ChatSession, command: ExecuteAgentCommand
    ) -> AsyncGenerator[str, None]:
        """Execute agent with streaming through runtime infrastructure."""
        # This would use the agent runtime for streaming execution
        # For now, yield placeholder chunks
        chunks = ["Response ", "from ", "agent ", agent.name]
        for chunk in chunks:
            yield chunk
    
    def get_events(self) -> List[object]:
        """Get domain events raised during execution."""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear domain events."""
        self._events.clear()
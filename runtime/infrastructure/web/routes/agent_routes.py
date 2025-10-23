"""Agent management routes - Infrastructure layer."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status

from ....application.commands.create_agent_command import CreateAgentCommand
from ....application.commands.update_agent_command import UpdateAgentCommand
from ....application.commands.delete_agent_command import DeleteAgentCommand
from ....application.commands.update_agent_status_command import UpdateAgentStatusCommand
from ....application.services.execute_agent_service import ExecuteAgentService
from ....application.services.create_agent_service import CreateAgentService
from ....application.services.query_agent_service import QueryAgentService
from ....application.services.update_agent_service import UpdateAgentService
from ....application.services.delete_agent_service import DeleteAgentService
from ....application.services.update_agent_status_service import UpdateAgentStatusService
from ....application.services.compose_agent_service import ComposeAgentService
from ....application.queries.get_agent_query import GetAgentQuery, ListAgentsQuery
from ....domain.value_objects.agent_id import AgentId
from ..models.requests import CreateAgentRequest, UpdateAgentRequest, UpdateAgentStatusRequest, ComposeAgentRequest
from ..models.responses import AgentResponse, CreateAgentResponse, ComposeAgentResponse
from ..dependencies import (
    get_create_agent_service, 
    get_query_agent_service,
    get_update_agent_service,
    get_delete_agent_service,
    get_update_agent_status_service,
    get_compose_agent_service
)
from ..auth import runtime_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post("/", response_model=CreateAgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: CreateAgentRequest,
    service: CreateAgentService = Depends(get_create_agent_service),
    _: bool = Depends(runtime_auth)
) -> CreateAgentResponse:
    """Create a new agent.
    
    Creates an agent configuration that can be used for chat execution.
    """
    try:
        # Parse request into structured models for better separation of concerns
        identity = request.get_identity()
        template = request.get_template()
        config = request.get_agent_configuration()
        
        # Convert HTTP request to domain command
        command = CreateAgentCommand(
            name=identity.name,
            template_id=template.template_id,
            configuration=config,
            template_version=template.get_template_version(),
            metadata=request.get_metadata(),
            agent_id=identity.id
        )
        
        # Execute use case
        agent = await service.execute(command)
        
        # Convert domain entity to HTTP response
        return CreateAgentResponse(
            success=True,
            agent_id=agent.id.value
        )
        
    except ValueError as e:
        logger.warning(f"Agent creation validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/compose", response_model=ComposeAgentResponse, status_code=status.HTTP_200_OK)
async def compose_agent(
    request: ComposeAgentRequest,
    service: ComposeAgentService = Depends(get_compose_agent_service),
    _: bool = Depends(runtime_auth)
) -> ComposeAgentResponse:
    """Compose an agent configuration from natural language instructions.
    
    This endpoint uses LLM to generate agent configuration parameters based on
    user instructions. The client is responsible for reviewing and confirming
    the generated configuration before creating the actual agent.
    """
    try:
        # Call composition service
        composed_config = await service.compose(
            template_id=request.template_id,
            instructions=request.instructions,
            suggested_name=request.suggested_name,
            suggested_tools=request.suggested_tools,
            llm_config_id=request.llm_config_id or "deepseek"
        )
        
        # Build response
        return ComposeAgentResponse(
            agent_id=composed_config["agent_id"],
            name=composed_config["name"],
            description=composed_config["description"],
            template_id=composed_config["template_id"],
            template_version_id=composed_config.get("template_version_id", "1.0.0"),
            system_prompt=composed_config["system_prompt"],
            template_config=composed_config["template_config"],
            toolsets=composed_config.get("toolsets", []),
            llm_config_id=request.llm_config_id or "deepseek",
            reasoning=composed_config.get("reasoning")
        )
        
    except ValueError as e:
        logger.warning(f"Agent composition failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to compose agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    service: QueryAgentService = Depends(get_query_agent_service),
    _: bool = Depends(runtime_auth)
) -> AgentResponse:
    """Get an agent by ID."""
    try:
        # Convert HTTP parameter to domain query
        agent_id_vo = AgentId.from_string(agent_id)
        query = GetAgentQuery(agent_id=agent_id_vo)
        
        # Execute query
        agent = await service.get_agent(query)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Convert domain entity to HTTP response
        return AgentResponse(
            id=agent.id.value,
            name=agent.name,
            template_id=agent.template_id,
            template_version=agent.template_version,
            status=agent.status.value,
            configuration=agent.configuration.to_dict(),
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            metadata=agent.metadata
        )
        
    except ValueError as e:
        logger.warning(f"Invalid agent ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID"
        )
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    template_id: Optional[str] = None,
    active_only: bool = False,
    limit: Optional[int] = None,
    offset: int = 0,
    service: QueryAgentService = Depends(get_query_agent_service),
    _: bool = Depends(runtime_auth)
) -> list[AgentResponse]:
    """List agents with optional filtering."""
    try:
        # Convert HTTP parameters to domain query
        query = ListAgentsQuery(
            template_id=template_id,
            active_only=active_only,
            limit=limit,
            offset=offset
        )
        
        # Execute query
        agents = await service.list_agents(query)
        
        # Convert domain entities to HTTP responses
        return [
            AgentResponse(
                id=agent.id.value,
                name=agent.name,
                template_id=agent.template_id,
                template_version=agent.template_version,
                status=agent.status.value,
                configuration=agent.configuration.to_dict(),
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                metadata=agent.metadata
            )
            for agent in agents
        ]
        
    except ValueError as e:
        logger.warning(f"Invalid query parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    service: UpdateAgentService = Depends(get_update_agent_service),
    _: bool = Depends(runtime_auth)
) -> AgentResponse:
    """Update an agent."""
    try:
        # Convert HTTP parameters to domain command
        agent_id_vo = AgentId.from_string(agent_id)
        command = UpdateAgentCommand(
            agent_id=agent_id_vo,
            name=request.name,
            template_id=request.template_id,
            template_version=request.template_version,
            configuration=request.get_agent_configuration(),
            metadata=request.metadata
        )
        
        # Execute command
        updated_agent = await service.execute(command)
        
        # Convert domain entity to HTTP response
        return AgentResponse(
            id=updated_agent.id.value,
            name=updated_agent.name,
            template_id=updated_agent.template_id,
            template_version=updated_agent.template_version,
            status=updated_agent.status.value,
            configuration=updated_agent.configuration.to_dict(),
            created_at=updated_agent.created_at,
            updated_at=updated_agent.updated_at,
            metadata=updated_agent.metadata
        )
        
    except ValueError as e:
        logger.warning(f"Agent update validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    service: DeleteAgentService = Depends(get_delete_agent_service),
    _: bool = Depends(runtime_auth)
) -> None:
    """Delete an agent."""
    try:
        # Convert HTTP parameter to domain command
        agent_id_vo = AgentId.from_string(agent_id)
        command = DeleteAgentCommand(agent_id=agent_id_vo)
        
        # Execute command
        await service.execute(command)
        
    except ValueError as e:
        logger.warning(f"Agent deletion validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: str,
    request: UpdateAgentStatusRequest,
    service: UpdateAgentStatusService = Depends(get_update_agent_status_service),
    _: bool = Depends(runtime_auth)
) -> AgentResponse:
    """Update an agent's status."""
    try:
        # Convert HTTP parameters to domain command
        agent_id_vo = AgentId.from_string(agent_id)
        command = UpdateAgentStatusCommand(
            agent_id=agent_id_vo,
            status=request.get_status()
        )
        
        # Execute command
        updated_agent = await service.execute(command)
        
        # Convert domain entity to HTTP response
        return AgentResponse(
            id=updated_agent.id.value,
            name=updated_agent.name,
            template_id=updated_agent.template_id,
            template_version=updated_agent.template_version,
            status=updated_agent.status.value,
            configuration=updated_agent.configuration.to_dict(),
            created_at=updated_agent.created_at,
            updated_at=updated_agent.updated_at,
            metadata=updated_agent.metadata
        )
        
    except ValueError as e:
        logger.warning(f"Agent status update validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
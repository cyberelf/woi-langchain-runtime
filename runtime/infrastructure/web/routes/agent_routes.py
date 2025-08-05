"""Agent management routes - Infrastructure layer."""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status

from ....application.commands.create_agent_command import CreateAgentCommand
from ....application.services.create_agent_service import CreateAgentService
from ....application.services.query_agent_service import QueryAgentService
from ....application.queries.get_agent_query import GetAgentQuery, ListAgentsQuery
from ....domain.value_objects.agent_id import AgentId
from ..models.requests import CreateAgentRequest, ListAgentsRequest
from ..models.responses import AgentResponse, ErrorResponse
from ..dependencies import get_create_agent_service, get_query_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: CreateAgentRequest,
    service: CreateAgentService = Depends(get_create_agent_service)
) -> AgentResponse:
    """Create a new agent.
    
    Creates an agent configuration that can be used for chat execution.
    """
    try:
        # Convert HTTP request to domain command
        command = CreateAgentCommand(
            name=request.name,
            template_id=request.template_id,
            configuration=request.configuration,
            template_version=request.template_version,
            metadata=request.metadata
        )
        
        # Execute use case
        agent = await service.execute(command)
        
        # Convert domain entity to HTTP response
        return AgentResponse(
            id=agent.id.value,
            name=agent.name,
            template_id=agent.template_id,
            template_version=agent.template_version,
            status=agent.status.value,
            configuration=agent.configuration,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            metadata=agent.metadata
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


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    service: QueryAgentService = Depends(get_query_agent_service)
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
            configuration=agent.configuration,
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


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    template_id: str = None,
    active_only: bool = False,
    limit: int = None,
    offset: int = 0,
    service: QueryAgentService = Depends(get_query_agent_service)
) -> List[AgentResponse]:
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
                configuration=agent.configuration,
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
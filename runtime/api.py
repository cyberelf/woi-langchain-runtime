"""FastAPI routes for the agent runtime API."""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer

from .auth import runtime_auth
from .config import settings
from .models import (
    AgentCreateRequest,
    AgentResponse,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
    HealthCheckItem,
    HealthMetrics,
    HealthResponse,
    SchemaResponse,
    ValidationResult,
)

# Create router
router = APIRouter()

# Security
security = HTTPBearer()

# Startup time for uptime calculation
startup_time = time.time()


def get_runtime(request: Request):
    """Get runtime instance from app state."""
    if not hasattr(request.app.state, "runtime"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Runtime not initialized",
        )
    return request.app.state.runtime


@router.post("/v1/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreateRequest,
    request: Request,
    _: bool = Depends(runtime_auth),
) -> AgentResponse:
    """Create a new agent."""
    try:
        runtime = get_runtime(request)
        
        # Create the agent using the new template system
        agent = runtime.agent_factory.create_agent(agent_data)
        
        return AgentResponse(
            success=True,
            agent_id=agent_data.id,
            message="Agent created successfully",
            validation_results=ValidationResult(
                valid=True,
                warnings=[],
            ),
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {e!s}",
        )


@router.put("/v1/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    agent_data: AgentCreateRequest,
    request: Request,
    _: bool = Depends(runtime_auth),
) -> AgentResponse:
    """Update an existing agent."""
    try:
        runtime = get_runtime(request)
        
        # Ensure the agent ID matches
        agent_data.id = agent_id
        
        # Update the agent using the new template system
        agent = runtime.agent_factory.update_agent(agent_id, agent_data)
        
        return AgentResponse(
            success=True,
            agent_id=agent_id,
            message="Agent updated successfully",
            validation_results=ValidationResult(
                valid=True,
                warnings=[],
            ),
        )
    
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {e!s}",
        )


@router.delete("/v1/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    request: Request,
    _: bool = Depends(runtime_auth),
) -> AgentResponse:
    """Delete an agent."""
    try:
        runtime = get_runtime(request)
        
        # Delete the agent using the new template system
        success = runtime.agent_factory.destroy_agent(agent_id)
        if not success:
            raise ValueError(f"Agent {agent_id} not found")
        
        return AgentResponse(
            success=True,
            agent_id=agent_id,
            message="Agent deleted successfully",
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {e!s}",
        )


@router.get("/v1/schema")
async def get_schema(
    request: Request,
    _: bool = Depends(runtime_auth),
) -> SchemaResponse:
    """Get runtime schema."""
    try:
        runtime = get_runtime(request)
        
        # Get schema from template manager
        return runtime.template_manager.generate_schema()
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schema: {e!s}",
        )


@router.post("/v1/chat/completions")
async def chat_completions(
    request_data: ChatCompletionRequest,
    request: Request,
    _: bool = Depends(runtime_auth),
) -> ChatCompletionResponse:
    """Execute agent chat completion."""
    try:
        runtime = get_runtime(request)
        
        # Get the agent
        agent = runtime.agent_factory.get_agent(request_data.model)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {request_data.model} not found",
            )
        
        # Handle streaming response
        if request_data.stream:
            async def generate_stream():
                try:
                    async for chunk in agent.stream_execute(
                        messages=request_data.messages,
                        temperature=request_data.temperature,
                        max_tokens=request_data.max_tokens,
                        metadata=getattr(request_data, "metadata", None),
                    ):
                        yield f"data: {chunk.model_dump_json()}\n\n"
                    
                    # Send final empty chunk
                    yield "data: [DONE]\n\n"
                
                except Exception as e:
                    error_chunk = ChatCompletionChunk(
                        id="chatcmpl-error",
                        object="chat.completion.chunk",
                        created=int(time.time()),
                        model=request_data.model,
                        choices=[],
                        error=str(e),
                    )
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/plain; charset=utf-8",
                },
            )
        
        else:
            # Non-streaming response
            response = await agent.execute(
                messages=request_data.messages,
                stream=False,
                temperature=request_data.temperature,
                max_tokens=request_data.max_tokens,
                metadata=getattr(request_data, "metadata", None),
            )
            
            # Update agent metrics
            runtime.agent_factory.update_agent_metrics(
                request_data.model,
                execution_time=0.0,  # Would be calculated from actual execution time
                error=False,
            )
            
            return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute agent: {e!s}",
        )


@router.get("/v1/health")
async def health_check(
    request: Request,
    _: bool = Depends(runtime_auth),
) -> HealthResponse:
    """Comprehensive health check."""
    try:
        runtime = get_runtime(request)
        
        # Get health status from runtime
        health_status = runtime.get_health_status()
        
        # Calculate uptime
        uptime_seconds = int(time.time() - startup_time)
        
        # Create health check items
        health_items = [
            HealthCheckItem(
                service="runtime",
                status="healthy" if health_status["initialized"] else "unhealthy",
                details={"templates_loaded": health_status.get("templates_loaded", 0)},
            ),
            HealthCheckItem(
                service="template_manager",
                status="healthy" if health_status.get("templates_loaded", 0) > 0 else "degraded",
                details={"template_count": health_status.get("templates_loaded", 0)},
            ),
            HealthCheckItem(
                service="agent_factory",
                status="healthy",
                details={"total_agents": health_status.get("total_agents", 0)},
            ),
            HealthCheckItem(
                service="scheduler",
                status="healthy",
                details={"active_agents": health_status.get("active_agents", 0)},
            ),
        ]
        
        # Determine overall status
        overall_status = "healthy"
        if any(item.status == "unhealthy" for item in health_items):
            overall_status = "unhealthy"
        elif any(item.status == "degraded" for item in health_items):
            overall_status = "degraded"
        
        # Create metrics
        metrics = HealthMetrics(
            uptime_seconds=uptime_seconds,
            total_agents=health_status.get("total_agents", 0),
            active_agents=health_status.get("active_agents", 0),
            templates_loaded=health_status.get("templates_loaded", 0),
        )
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            checks=health_items,
            metrics=metrics,
        )
    
    except Exception as e:
        # Return degraded health if we can't get status
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            checks=[
                HealthCheckItem(
                    service="runtime",
                    status="unhealthy",
                    details={"error": str(e)},
                ),
            ],
            metrics=HealthMetrics(
                uptime_seconds=int(time.time() - startup_time),
                total_agents=0,
                active_agents=0,
                templates_loaded=0,
            ),
        )

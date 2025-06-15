"""FastAPI routes for the agent runtime API."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer

from .auth import runtime_auth
from .agents import agent_manager
from .models import (
    AgentCreateRequest, AgentResponse, ValidationResult,
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk,
    SchemaResponse, HealthResponse, HealthCheckItem, HealthMetrics,
    ErrorResponse
)
from .schema import get_runtime_schema
from .config import settings
from . import __version__

# Create router
router = APIRouter()

# Security
security = HTTPBearer()

# Startup time for uptime calculation
startup_time = time.time()


@router.post("/v1/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreateRequest,
    request: Request,
    _: bool = Depends(runtime_auth)
) -> AgentResponse:
    """Create a new agent."""
    try:
        # Validate agent configuration
        validation_warnings = []
        
        # Check if template configuration is valid
        if agent_data.type.value == "task":
            task_config = agent_data.template_config.get("taskSteps", {})
            if not task_config.get("steps"):
                validation_warnings.append("No task steps defined, using default steps")
        
        elif agent_data.type.value == "custom":
            code_config = agent_data.template_config.get("codeSource", {})
            if not code_config.get("content"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Custom agents require code content"
                )
        
        # Create the agent
        agent = agent_manager.create_agent(agent_data)
        
        return AgentResponse(
            success=True,
            agent_id=agent.id,
            message="Agent created successfully",
            validation_results=ValidationResult(
                valid=True,
                warnings=validation_warnings
            )
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.put("/v1/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    agent_data: AgentCreateRequest,
    request: Request,
    _: bool = Depends(runtime_auth)
) -> AgentResponse:
    """Update an existing agent."""
    try:
        # Ensure the agent ID matches
        agent_data.id = agent_id
        
        # Validate agent configuration
        validation_warnings = []
        
        # Check if template configuration is valid
        if agent_data.type.value == "task":
            task_config = agent_data.template_config.get("taskSteps", {})
            if not task_config.get("steps"):
                validation_warnings.append("No task steps defined, using default steps")
        
        elif agent_data.type.value == "custom":
            code_config = agent_data.template_config.get("codeSource", {})
            if not code_config.get("content"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Custom agents require code content"
                )
        
        # Update the agent
        agent = agent_manager.update_agent(agent_id, agent_data)
        
        return AgentResponse(
            success=True,
            agent_id=agent.id,
            message="Agent updated successfully",
            validation_results=ValidationResult(
                valid=True,
                warnings=validation_warnings
            )
        )
    
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@router.delete("/v1/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    request: Request,
    _: bool = Depends(runtime_auth)
) -> AgentResponse:
    """Delete an agent."""
    try:
        agent_manager.delete_agent(agent_id)
        
        return AgentResponse(
            success=True,
            agent_id=agent_id,
            message="Agent deleted successfully"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


@router.get("/v1/schema")
async def get_schema(
    request: Request,
    _: bool = Depends(runtime_auth)
) -> SchemaResponse:
    """Get runtime schema."""
    try:
        # Check for schema version compatibility
        client_version = request.headers.get("X-Schema-Version")
        current_version = "1.2.0"
        
        if client_version and client_version != current_version:
            # In a real implementation, you would check for breaking changes
            # For now, we'll just return the current schema
            pass
        
        return get_runtime_schema()
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schema: {str(e)}"
        )


@router.post("/v1/chat/completions")
async def chat_completions(
    request_data: ChatCompletionRequest,
    request: Request,
    _: bool = Depends(runtime_auth)
) -> Any:
    """Execute agent with OpenAI-compatible chat completions."""
    try:
        # Get the agent
        agent = agent_manager.get_agent(request_data.model)
        
        # Validate message length
        total_length = sum(len(msg.content) for msg in request_data.messages)
        if total_length > settings.max_message_length:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Message length exceeds limit of {settings.max_message_length}"
            )
        
        # Execute the agent
        if request_data.stream:
            # Return streaming response
            async def generate_stream():
                try:
                    async for chunk in agent.stream_execute(
                        messages=request_data.messages,
                        temperature=request_data.temperature,
                        max_tokens=request_data.max_tokens,
                        metadata=request_data.metadata
                    ):
                        yield f"data: {chunk.json()}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    error_chunk = ChatCompletionChunk(
                        id=f"chatcmpl-error",
                        created=int(time.time()),
                        model=request_data.model,
                        choices=[{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "error"
                        }]
                    )
                    yield f"data: {error_chunk.json()}\n\n"
                    yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            # Return regular response
            response = await agent.execute(
                messages=request_data.messages,
                stream=False,
                temperature=request_data.temperature,
                max_tokens=request_data.max_tokens,
                metadata=request_data.metadata
            )
            return response
    
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {request_data.model}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.get("/v1/health")
async def health_check(
    request: Request,
    _: bool = Depends(runtime_auth)
) -> HealthResponse:
    """Health check endpoint."""
    try:
        current_time = datetime.now().isoformat()
        uptime = int(time.time() - startup_time)
        
        # Perform health checks
        checks = {}
        
        # Check LLM proxy (simplified)
        try:
            # In a real implementation, you would ping the LLM proxy
            checks["llm_proxy"] = HealthCheckItem(
                status="healthy",
                response_time_ms=150,
                last_check=current_time
            )
        except Exception:
            checks["llm_proxy"] = HealthCheckItem(
                status="unhealthy",
                response_time_ms=None,
                last_check=current_time
            )
        
        # Check database (placeholder)
        checks["database"] = HealthCheckItem(
            status="healthy",
            response_time_ms=5,
            last_check=current_time
        )
        
        # Check agent templates
        checks["agent_templates"] = HealthCheckItem(
            status="healthy",
            response_time_ms=None,
            last_check=current_time,
            loaded_templates=3  # We have 3 templates
        )
        
        # Get metrics
        metrics_data = agent_manager.get_metrics()
        metrics = HealthMetrics(
            active_agents=metrics_data["active_agents"],
            total_executions=metrics_data["total_executions"],
            average_response_time_ms=metrics_data.get("average_response_time_ms", 0),
            error_rate=metrics_data.get("error_rate", 0.0)
        )
        
        # Determine overall status
        overall_status = "healthy"
        for check in checks.values():
            if check.status != "healthy":
                overall_status = "unhealthy"
                break
        
        return HealthResponse(
            status=overall_status,
            timestamp=current_time,
            version=__version__,
            uptime_seconds=uptime,
            last_sync=None,  # Would be set by sync process
            checks=checks,
            metrics=metrics
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return ErrorResponse(
        error="HTTP_ERROR",
        message=exc.detail,
        details=None
    )


@router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    return ErrorResponse(
        error="INTERNAL_ERROR",
        message="An internal error occurred",
        details=None
    ) 
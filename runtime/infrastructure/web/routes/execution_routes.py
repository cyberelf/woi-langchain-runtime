"""Agent execution routes - Infrastructure layer using new task management architecture."""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from ....application.commands.execute_agent_command import ExecuteAgentCommand
from ....application.services.execute_agent_service import ExecuteAgentServiceAdapter
from ..models.requests import ChatCompletionRequest
from ..models.responses import (
    ChatCompletionResponse, 
    ChatCompletionChoice, 
    ChatCompletionUsage,
    ChatMessageResponse,
    StreamingChunk
)
from ..dependencies import get_execute_agent_service
from ....auth import runtime_auth
from ....domain.value_objects.chat_message import MessageRole, ChatMessage
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["execution"])


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    service: ExecuteAgentServiceAdapter = Depends(get_execute_agent_service),
    _: bool = Depends(runtime_auth)
) -> ChatCompletionResponse:
    """Execute agent using OpenAI-compatible chat completions format.
    
    This endpoint provides OpenAI-compatible agent execution, allowing
    seamless integration with existing OpenAI client libraries.
    
    Uses the new async task management architecture for improved performance
    and scalability.
    """
    try:
        # Convert HTTP request to domain command using proper value objects
        messages = []
        for msg in request.messages:
            # Convert from OpenAI format to domain ChatMessage
            role = MessageRole(msg.role.value)
            chat_message = ChatMessage(
                role=role,
                content=msg.content,
                timestamp=datetime.now(UTC),
                metadata={"name": getattr(msg, 'name', None)} if hasattr(msg, 'name') else {}
            )
            messages.append(chat_message)
        
        command = ExecuteAgentCommand(
            agent_id=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stream=request.stream,
            stop=request.stop,
            session_id=request.get_session_id(),
            user_id=request.get_user_id(),
            metadata=request.metadata
        )
        
        # Handle streaming vs non-streaming
        if request.stream:
            # Return streaming response using new task manager
            return StreamingResponse(
                _stream_chat_completion(service, command),
                media_type="text/plain"
            )
        else:
            # Execute agent and get result via task manager
            result = await service.execute(command)
            
            # Convert result to OpenAI-compatible response
            return _convert_to_chat_completion_response(result)
        
    except ValueError as e:
        logger.warning(f"Agent execution validation failed: {e}")
        
        # Check if it's an agent not found error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to execute agent: {e}")
        
        # Check if it's an agent not found error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {request.model} not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def _stream_chat_completion(
    service: ExecuteAgentServiceAdapter, 
    command: ExecuteAgentCommand
) -> AsyncGenerator[str, None]:
    """Stream chat completion chunks in OpenAI format using new task manager."""
    try:
        # Use the new async task management streaming
        async for chunk in service._execute_streaming_real(None, command.messages, command, 0):
            # Format as Server-Sent Events
            chunk_data = StreamingChunk(**chunk)
            yield f"data: {chunk_data.model_dump_json()}\n\n"
        
        # Send final [DONE] message
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Streaming execution failed: {e}")
        # Send error chunk
        error_chunk = {
            "id": "error",
            "object": "chat.completion.chunk",
            "created": int(command.metadata.get("created", 0)) if command.metadata else 0,
            "model": command.agent_id,
            "choices": [{
                "index": 0,
                "delta": {"content": f"Error: {str(e)}"},
                "finish_reason": "error"
            }]
        }
        yield f"data: {StreamingChunk(**error_chunk).model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"


def _convert_to_chat_completion_response(result) -> ChatCompletionResponse:
    """Convert execution result to OpenAI-compatible response."""
    
    # Create the response message
    message = ChatMessageResponse(
        role=MessageRole.ASSISTANT,
        content=result.message,
        timestamp=datetime.fromtimestamp(result.created_at, UTC),
        metadata=result.metadata
    )
    
    # Create the choice
    choice = ChatCompletionChoice(
        index=0,
        message=message,
        finish_reason=result.finish_reason
    )
    
    # Create usage statistics
    usage = ChatCompletionUsage(
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens
    )
    
    # Create the complete response
    return ChatCompletionResponse(
        id=result.response_id,
        object="chat.completion",
        created=result.created_at,
        model=result.agent_id,
        choices=[choice],
        usage=usage,
        metadata=result.metadata
    )
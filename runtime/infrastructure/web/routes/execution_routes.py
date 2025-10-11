"""Agent execution routes - Infrastructure layer using new task management architecture."""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from collections.abc import AsyncGenerator
import time
import uuid

from ....application.commands.execute_agent_command import ExecuteAgentCommand
from ....application.services.execute_agent_service import ExecuteAgentService
from ....core.executors import ExecutionResult
from ..models.requests import ChatCompletionRequest
from ..models.responses import (
    ChatCompletionResponse, 
    ChatCompletionChoice, 
    ChatCompletionUsage,
    ChatMessageResponse,
    StreamingChunk,
    StreamingChunkChoice,
    StreamingChunkDelta
)
from ..dependencies import get_execute_agent_service
from ..auth import runtime_auth
from ....domain.value_objects.chat_message import MessageRole, ChatMessage
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["execution"])


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    responses={
        200: {
            "description": "Chat completion response",
            "model": ChatCompletionResponse,
        },
        "200.streaming": {
            "description": "Server-sent events stream for real-time completion",
            "content": {"text/event-stream": {"example": "data: {...}\n\n"}},
        }
    }
)
async def chat_completions(
    request: ChatCompletionRequest,
    service: ExecuteAgentService = Depends(get_execute_agent_service),
    _: bool = Depends(runtime_auth)
):
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
        
        # Check if agent exists before execution
        agent_exists = await service.agent_exists(request.model)
        if not agent_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {request.model} not found"
            )

        # Handle streaming vs non-streaming
        logger.debug(f"🎯 Request routing - stream: {request.stream}, agent: {request.model}")

        if request.stream:
            logger.info(f"🌊 Routing to streaming execution for agent: {request.model}")
            # Return streaming response with correct SSE format
            return StreamingResponse(
                _stream_chat_completion(service, command),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        else:
            logger.info(f"⚡ Routing to synchronous execution for agent: {request.model}")
            # Execute agent and get ExecutionResult
            execution_result = await service.execute(command)

            logger.debug(f"📊 Execution completed - success: {execution_result.success}, "
                        f"tokens: {execution_result.total_tokens}, "
                        f"time: {execution_result.processing_time_ms}ms")

            # Handle execution result based on success status
            if not execution_result.success:
                error_message = execution_result.error or "Execution failed"

                # For execution errors, return 400
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
                )

            # Convert successful execution result to OpenAI-compatible response
            response = _convert_execution_result_to_chat_completion(execution_result, request.model)

            # FastAPI will automatically validate this against ChatCompletionResponse
            return response
        
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
        logger.error(f"Failed to execute agent: {str(e)}")
        
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
    service: ExecuteAgentService, 
    command: ExecuteAgentCommand
) -> AsyncGenerator[str, None]:
    """Stream chat completion chunks in OpenAI SSE format."""    
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created_timestamp = int(time.time())
    
    logger.info(f"🌊 Starting SSE stream for agent {command.agent_id} "
               f"(completion_id: {completion_id})")
    logger.debug(f"🔍 Stream request details - messages: {len(command.messages)}, "
                f"session: {command.session_id}")
    
    chunk_count = 0
    total_content_length = 0
    stream_start = time.time()
    
    try:
        # Stream core chunks from application service
        logger.debug("📺 Starting core chunk consumption from service")
        async for core_chunk in service.execute_streaming(command):
            chunk_count += 1
            content = core_chunk.content or ""
            total_content_length += len(content)
            
            logger.debug(f"📦 SSE chunk #{chunk_count}: {len(content)} chars, "
                        f"finish_reason: {core_chunk.finish_reason}")
            
            # Convert core StreamingChunk to OpenAI web format
            openai_chunk = StreamingChunk(
                id=completion_id,
                object="chat.completion.chunk",
                created=created_timestamp,
                model=command.agent_id,
                system_fingerprint="",
                choices=[StreamingChunkChoice(
                    index=0,
                    delta=StreamingChunkDelta(role="agent", content=content),
                    finish_reason=core_chunk.finish_reason
                )],
                metadata={
                    "task_id": core_chunk.task_id,
                    "message_id": core_chunk.message_id,
                    "context_id": core_chunk.context_id,
                    **(core_chunk.metadata or {})
                }
            )
            
            # Format as Server-Sent Event
            sse_data = f"data: {openai_chunk.model_dump_json()}\n\n"
            logger.debug(f"📤 SSE data size: {len(sse_data)} bytes")
            yield sse_data
            
            # Log completion when stream finishes
            if core_chunk.finish_reason:
                stream_time = (time.time() - stream_start) * 1000
                logger.info(f"✅ SSE stream completed for {command.agent_id}: "
                           f"{chunk_count} chunks, {total_content_length} chars, "
                           f"{stream_time:.2f}ms total")
                break
        
        # Send final [DONE] message
        logger.debug("🏁 Sending [DONE] marker")
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        stream_time = (time.time() - stream_start) * 1000
        logger.error(f"❌ SSE streaming failed for {command.agent_id} after "
                    f"{chunk_count} chunks, {stream_time:.2f}ms: {e}")
        
        # Send error chunk
        error_chunk = StreamingChunk(
            id=completion_id,
            object="chat.completion.chunk",
            created=created_timestamp,
            model=command.agent_id,
            system_fingerprint="",
            choices=[StreamingChunkChoice(
                index=0,
                delta=StreamingChunkDelta(content=f"Error: {str(e)}"),
                finish_reason="error"
            )]
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"


def _convert_execution_result_to_chat_completion(
    execution_result: ExecutionResult, 
    model_id: str
) -> ChatCompletionResponse:
    """Convert core ExecutionResult to OpenAI-compatible ChatCompletionResponse."""    
    # Handle failed execution
    if not execution_result.success:
        error_message = execution_result.error or "Execution failed"
        message = ChatMessageResponse(
            role=MessageRole.ASSISTANT,
            content=f"Error: {error_message}",
            timestamp=datetime.now(UTC),
            metadata=execution_result.metadata or {}
        )
        
        choice = ChatCompletionChoice(
            index=0,
            message=message,
            finish_reason="error"
        )
    else:
        # Successful execution
        message = ChatMessageResponse(
            role=MessageRole.ASSISTANT,
            content=execution_result.message or "",
            timestamp=datetime.now(UTC),
            metadata=execution_result.metadata or {}
        )
        
        choice = ChatCompletionChoice(
            index=0,
            message=message,
            finish_reason=execution_result.finish_reason or "stop"
        )
    
    # Create usage statistics
    usage = ChatCompletionUsage(
        prompt_tokens=execution_result.prompt_tokens or 0,
        completion_tokens=execution_result.completion_tokens or 0,
        total_tokens=(execution_result.prompt_tokens or 0) + (execution_result.completion_tokens or 0)
    )
    
    # Create the complete response
    return ChatCompletionResponse(
        id=execution_result.message_id or f"chatcmpl-{uuid.uuid4().hex[:8]}",
        object="chat.completion",
        created=int(time.time()),
        model=model_id,
        choices=[choice],
        usage=usage,
        metadata={
            "task_id": execution_result.task_id,
            "message_id": execution_result.message_id,
            "context_id": execution_result.context_id,
            **execution_result.metadata
        }
    )
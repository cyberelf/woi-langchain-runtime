"""Main client SDK for LangChain Agent Runtime.

This module provides a high-level client interface for interacting with
the agent runtime via HTTP.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional
import httpx

from .models import (
    AgentInfo,
    ChatCompletionResponse,
    ChatMessage,
    CreateAgentRequest,
    RuntimeStatus,
    StreamingChunk,
    TemplateInfo,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:8000/v1/"


class RuntimeClient:
    """
    High-level asynchronous client for the LangChain Agent Runtime API.
    
    This client provides convenient methods for:
    - Listing and discovering templates
    - Managing agent lifecycle
    - Interactive chat sessions
    - Runtime health monitoring
    """

    def __init__(
        self, base_url: str = DEFAULT_BASE_URL, api_key: Optional[str] = None, timeout: float = 30.0
    ):
        """
        Initialize the runtime client.
        
        Args:
            base_url: The base URL of the runtime API.
            api_key: The API key (runtime token) for authentication. 
                If None, requests will be made without authentication.
            timeout: Default timeout for HTTP requests.
        """
        self.base_url = base_url
        self.api_key = api_key
        
        # Set up default headers
        headers = {}
        if self.api_key:
            headers["X-Runtime-Token"] = self.api_key
        
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url, 
            headers=headers,
            timeout=timeout
        )
        self._status = RuntimeStatus.DISCONNECTED

    async def shutdown(self) -> None:
        """Shutdown the client and cleanup resources."""
        await self.http_client.aclose()
        self._status = RuntimeStatus.DISCONNECTED
        logger.info("Runtime client shutdown complete")

    @property
    def status(self) -> RuntimeStatus:
        """Get current runtime connection status."""
        # In HTTP client, status is more about reachability.
        # A proper implementation might ping the health endpoint.
        return self._status

    @property
    def is_connected(self) -> bool:
        """Check if runtime is considered connected."""
        # This is simplified. A real check would involve a health check.
        return self._status == RuntimeStatus.CONNECTED

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Helper method for making authenticated requests."""
        try:
            response = await self.http_client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            # If request is successful, we can assume connection is fine
            self._status = RuntimeStatus.CONNECTED
            return response
        except httpx.HTTPStatusError as e:
            # Provide more specific error messages for authentication failures
            if e.response.status_code == 401:
                logger.error(f"Authentication failed: {e.response.text}")
                self._status = RuntimeStatus.ERROR
                raise httpx.HTTPStatusError(
                    message=f"Authentication failed. Please check your API key. Details: {e.response.text}",
                    request=e.request,
                    response=e.response
                )
            logger.error(
                f"HTTP error for {e.request.method} {e.request.url}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            self._status = RuntimeStatus.ERROR
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {e.request.method} {e.request.url}: {e}")
            self._status = RuntimeStatus.DISCONNECTED
            raise

    # Template Management Methods

    async def list_templates(self, framework: Optional[str] = None) -> list[TemplateInfo]:
        """List all available templates."""
        params = {}
        if framework:
            params["framework"] = framework
        
        response = await self._request("GET", "templates/", params=params)
        response_data = response.json()
        return [TemplateInfo(**t) for t in response_data.get("templates", [])]

    async def get_template(self, template_id: str, version: Optional[str] = None) -> Optional[TemplateInfo]:
        """Get information about a specific template."""
        endpoint = f"templates/{template_id}"
        params = {}
        if version:
            params["version"] = version

        try:
            response = await self._request("GET", endpoint, params=params)
            return TemplateInfo(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # Agent Management Methods

    async def list_agents(self) -> list[AgentInfo]:
        """List all existing agents."""
        response = await self._request("GET", "agents/")
        agents_data = response.json()
        return [AgentInfo(**agent_data) for agent_data in agents_data]

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent."""
        try:
            response = await self._request("GET", f"agents/{agent_id}")
            return AgentInfo(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def create_agent(self, agent_request: CreateAgentRequest) -> AgentInfo:
        """Create a new agent."""
        # Create the agent and get the creation response
        response = await self._request("POST", "agents/", json=agent_request.model_dump())
        create_response = response.json()
        
        # The server returns CreateAgentResponse: {"success": bool, "agent_id": str}
        if not create_response.get("success"):
            raise RuntimeError("Agent creation failed")
        
        agent_id = create_response.get("agent_id")
        if not agent_id:
            raise RuntimeError("Agent creation succeeded but no agent_id returned")
            
        # Fetch the full agent info to return consistent AgentInfo
        agent_info = await self.get_agent(agent_id)
        if not agent_info:
            raise RuntimeError(f"Created agent {agent_id} but failed to retrieve it")
            
        return agent_info

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an existing agent."""
        try:
            await self._request("DELETE", f"agents/{agent_id}")
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    # Interactive Chat Methods

    async def chat_with_agent(
        self,
        agent_id: str,
        messages: list[ChatMessage],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> ChatCompletionResponse:
        """Send messages to an agent and get a response using OpenAI-compatible format."""
        if stream:
            raise NotImplementedError("Use stream_chat_with_agent for streaming responses.")

        # Build OpenAI-compatible request payload
        payload = {
            "model": agent_id,
            "messages": [{"role": msg.role.value, "content": msg.content} for msg in messages],
            "stream": False
        }
        
        # Add optional parameters
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if metadata is not None:
            payload["metadata"] = metadata

        response = await self._request("POST", "chat/completions", json=payload)
        return ChatCompletionResponse(**response.json())

    async def stream_chat_with_agent(
        self,
        agent_id: str,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream chat response from an agent using OpenAI-compatible format."""
        # Build OpenAI-compatible request payload for streaming
        payload = {
            "model": agent_id,
            "messages": [{"role": msg.role.value, "content": msg.content} for msg in messages],
            "stream": True
        }
        
        # Add optional parameters
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if metadata is not None:
            payload["metadata"] = metadata

        async with self.http_client.stream("POST", "chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[len("data: "):]
                    if data.strip() == "[DONE]":
                        break
                    chunk_data = json.loads(data)
                    yield StreamingChunk.model_validate(chunk_data)

    # Health and Status Methods

    async def get_health_status(self) -> dict[str, Any]:
        """Get runtime health status."""
        try:
            response = await self._request("GET", "health/")
            self._status = RuntimeStatus.CONNECTED
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            self._status = RuntimeStatus.ERROR
            return {"status": "error", "detail": str(e)}


# Convenience function for creating a client
async def create_client(
    base_url: str = DEFAULT_BASE_URL, api_key: Optional[str] = None
) -> "RuntimeClient":
    """
    Create a runtime client.
    
    Args:
        base_url: The base URL for the runtime API.
        api_key: The API key (runtime token) for authentication.

    Returns:
        A RuntimeClient instance.
    """
    return RuntimeClient(base_url=base_url, api_key=api_key)


# Context manager for automatic cleanup
class RuntimeClientContext:
    """Context manager for automatic client initialization and cleanup."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: Optional[str] = None, timeout: float = 300.0):
        self._client = RuntimeClient(base_url=base_url, api_key=api_key, timeout=timeout)
    
    async def __aenter__(self) -> "RuntimeClient":
        # No explicit initialization needed anymore.
        # The client is ready to make requests upon instantiation.
        return self._client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.shutdown()

"""LLM client for communicating with LLM Proxy service."""

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Optional, Protocol

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .models import ChatMessage, MessageRole


class LLMClient(Protocol):
    """Protocol for LLM clients."""
    
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        llm_config_id: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send chat completion request."""
        ...
    
    async def stream_chat_completion(
        self,
        messages: list[ChatMessage],
        llm_config_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion."""
        ...


class LLMProxyClient:
    """Client for LLM Proxy service."""
    
    def __init__(self, proxy_url: Optional[str] = None, proxy_token: Optional[str] = None) -> None:
        self.proxy_url = proxy_url or settings.llm_proxy_url
        self.proxy_token = proxy_token or settings.llm_proxy_token
        self.timeout = settings.llm_request_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def __aenter__(self) -> "LLMProxyClient":
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.client.aclose()
    
    def _prepare_headers(self, llm_config_id: str) -> dict[str, str]:
        """Prepare headers for LLM Proxy request."""
        headers = {
            "Content-Type": "application/json",
            "X-LLM-Config-ID": llm_config_id,
        }
        
        if self.proxy_token:
            headers["Authorization"] = f"Bearer {self.proxy_token}"
        
        return headers
    
    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        """Convert ChatMessage objects to LLM Proxy format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        llm_config_id: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send chat completion request to LLM Proxy."""
        headers = self._prepare_headers(llm_config_id)
        
        payload = {
            "messages": self._convert_messages(messages),
            "stream": stream,
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        # Add any additional parameters
        payload.update(kwargs)
        
        try:
            response = await self.client.post(
                f"{self.proxy_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM Proxy request failed: {e}")
    
    async def stream_chat_completion(
        self,
        messages: list[ChatMessage],
        llm_config_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion from LLM Proxy."""
        headers = self._prepare_headers(llm_config_id)
        
        payload = {
            "messages": self._convert_messages(messages),
            "stream": True,
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        payload.update(kwargs)
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.proxy_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
        
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM Proxy streaming request failed: {e}")


class FallbackLLMClient:
    """Fallback LLM client using direct OpenAI integration."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.openai_api_key = api_key or settings.openai_api_key
        self.openai_base_url = base_url or settings.openai_base_url
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required for fallback LLM client")
        
        self.llm = ChatOpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
            model="gpt-3.5-turbo",
            temperature=0.7,
            timeout=settings.llm_request_timeout,
        )
    
    def _convert_to_langchain_messages(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert ChatMessage objects to LangChain messages."""
        langchain_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=msg.content))
        
        return langchain_messages
    
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        llm_config_id: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send chat completion request using direct OpenAI integration."""
        langchain_messages = self._convert_to_langchain_messages(messages)
        
        # Update LLM parameters if provided
        if temperature is not None:
            self.llm.temperature = temperature
        
        if max_tokens is not None:
            self.llm.max_tokens = max_tokens
        
        try:
            if stream:
                # For streaming, we'll need to handle it differently
                # This is a simplified implementation
                response = await self.llm.ainvoke(langchain_messages)
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": response.content,
                        },
                        "finish_reason": "stop",
                    }],
                    "usage": {
                        "prompt_tokens": 0,  # Would need to calculate
                        "completion_tokens": 0,  # Would need to calculate
                        "total_tokens": 0,
                    },
                }
            else:
                response = await self.llm.ainvoke(langchain_messages)
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": response.content,
                        },
                        "finish_reason": "stop",
                    }],
                    "usage": {
                        "prompt_tokens": 0,  # Would need to calculate
                        "completion_tokens": 0,  # Would need to calculate
                        "total_tokens": 0,
                    },
                }
        
        except Exception as e:
            raise RuntimeError(f"Fallback LLM request failed: {e}")


class LLMClientWithFallback:
    """Manager for LLM clients with fallback support."""
    
    def __init__(
        self, 
        proxy_client: Optional[LLMProxyClient] = None,
        fallback_client: Optional[FallbackLLMClient] = None,
    ) -> None:
        self.proxy_client = proxy_client
        self.fallback_client = fallback_client
    
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        llm_config_id: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send chat completion request with fallback support."""
        # Try proxy client first
        if self.proxy_client:
            try:
                async with self.proxy_client:
                    return await self.proxy_client.chat_completion(
                        messages=messages,
                        llm_config_id=llm_config_id,
                        stream=stream,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )
            except Exception as e:
                print(f"LLM Proxy failed, trying fallback: {e}")
        
        # Fall back to direct OpenAI client
        if self.fallback_client:
            return await self.fallback_client.chat_completion(
                messages=messages,
                llm_config_id=llm_config_id,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        
        raise RuntimeError("No LLM client available")
    
    async def stream_chat_completion(
        self,
        messages: list[ChatMessage],
        llm_config_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion with fallback support."""
        # Try proxy client first
        if self.proxy_client:
            try:
                async with self.proxy_client:
                    async for chunk in self.proxy_client.stream_chat_completion(
                        messages=messages,
                        llm_config_id=llm_config_id,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    ):
                        yield chunk
                    return
            except Exception as e:
                print(f"LLM Proxy streaming failed, trying fallback: {e}")
        
        # Fall back to direct OpenAI client (simplified streaming)
        if self.fallback_client:
            response = await self.fallback_client.chat_completion(
                messages=messages,
                llm_config_id=llm_config_id,
                stream=False,  # Fallback doesn't support streaming
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            
            # Simulate streaming by yielding the complete response
            yield {
                "choices": [{
                    "delta": {
                        "role": "assistant",
                        "content": response["choices"][0]["message"]["content"],
                    },
                    "finish_reason": "stop",
                }],
                "usage": response.get("usage"),
            }
            return
        
        raise RuntimeError("No LLM client available for streaming")


class LLMClientFactory:
    """Factory for creating LLM clients based on configuration."""
    
    def __init__(self) -> None:
        self._default_client: Optional[LLMClientWithFallback] = None
    
    def create_default_client(self) -> LLMClient:
        """Create a default LLM client manager."""
        if self._default_client is None:
            proxy_client = None
            fallback_client = None
            
            # Initialize proxy client if configured
            if settings.llm_proxy_url:
                proxy_client = LLMProxyClient()
            
            # Initialize fallback client if OpenAI key is available
            if settings.openai_api_key:
                try:
                    fallback_client = FallbackLLMClient()
                except ValueError:
                    pass  # Fallback not available
            
            self._default_client = LLMClientWithFallback(
                proxy_client=proxy_client,
                fallback_client=fallback_client,
            )
        
        return self._default_client
    
    def create_proxy_client(
        self, 
        proxy_url: Optional[str] = None, 
        proxy_token: Optional[str] = None,
    ) -> LLMProxyClient:
        """Create a proxy client with custom configuration."""
        return LLMProxyClient(proxy_url=proxy_url, proxy_token=proxy_token)
    
    def create_fallback_client(
        self, 
        api_key: Optional[str] = None, 
        base_url: Optional[str] = None,
    ) -> FallbackLLMClient:
        """Create a fallback client with custom configuration."""
        return FallbackLLMClient(api_key=api_key, base_url=base_url)
    
    def create_client_for_llm_config(self, llm_config_id: str) -> LLMClient:
        """Create an LLM client for specific configuration."""
        # TODO: In the future, this could fetch specific LLM configuration
        # from a database or configuration service based on llm_config_id
        # For now, return the default client
        return self.create_default_client()


# Factory instance for dependency injection
llm_client_factory = LLMClientFactory()


def get_default_llm_client() -> LLMClient:
    """Dependency provider for default LLM client."""
    return llm_client_factory.create_default_client()

def get_llm_client_factory() -> LLMClientFactory:
    """Dependency provider for LLM client factory."""
    return llm_client_factory
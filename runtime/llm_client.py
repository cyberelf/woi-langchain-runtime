"""LLM client for communicating with LLM Proxy service."""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .models import ChatMessage, MessageRole


class LLMProxyClient:
    """Client for LLM Proxy service."""
    
    def __init__(self) -> None:
        self.proxy_url = settings.llm_proxy_url
        self.proxy_token = settings.llm_proxy_token
        self.timeout = settings.llm_request_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def __aenter__(self) -> "LLMProxyClient":
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.client.aclose()
    
    def _prepare_headers(self, llm_config_id: str) -> Dict[str, str]:
        """Prepare headers for LLM Proxy request."""
        headers = {
            "Content-Type": "application/json",
            "X-LLM-Config-ID": llm_config_id
        }
        
        if self.proxy_token:
            headers["Authorization"] = f"Bearer {self.proxy_token}"
        
        return headers
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert ChatMessage objects to LLM Proxy format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        llm_config_id: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Send chat completion request to LLM Proxy."""
        headers = self._prepare_headers(llm_config_id)
        
        payload = {
            "messages": self._convert_messages(messages),
            "stream": stream
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
                json=payload
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM Proxy request failed: {e}")
    
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        llm_config_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion from LLM Proxy."""
        headers = self._prepare_headers(llm_config_id)
        
        payload = {
            "messages": self._convert_messages(messages),
            "stream": True
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
                json=payload
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
    
    def __init__(self) -> None:
        self.openai_api_key = settings.openai_api_key
        self.openai_base_url = settings.openai_base_url
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required for fallback LLM client")
        
        self.llm = ChatOpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
            model="gpt-3.5-turbo",
            temperature=0.7,
            timeout=settings.llm_request_timeout
        )
    
    def _convert_to_langchain_messages(self, messages: List[ChatMessage]) -> List[BaseMessage]:
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
        messages: List[ChatMessage],
        llm_config_id: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
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
                            "content": response.content
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 0,  # Would need to calculate
                        "completion_tokens": 0,  # Would need to calculate
                        "total_tokens": 0
                    }
                }
            else:
                response = await self.llm.ainvoke(langchain_messages)
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": response.content
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 0,  # Would need to calculate
                        "completion_tokens": 0,  # Would need to calculate
                        "total_tokens": 0
                    }
                }
        
        except Exception as e:
            raise RuntimeError(f"Fallback LLM request failed: {e}")


class LLMClientManager:
    """Manager for LLM clients with fallback support."""
    
    def __init__(self) -> None:
        self.proxy_client: Optional[LLMProxyClient] = None
        self.fallback_client: Optional[FallbackLLMClient] = None
        
        # Initialize proxy client if configured
        if settings.llm_proxy_url:
            self.proxy_client = LLMProxyClient()
        
        # Initialize fallback client if OpenAI key is available
        if settings.openai_api_key:
            try:
                self.fallback_client = FallbackLLMClient()
            except ValueError:
                pass  # Fallback not available
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        llm_config_id: str,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
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
                        **kwargs
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
                **kwargs
            )
        
        raise RuntimeError("No LLM client available")
    
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        llm_config_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
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
                        **kwargs
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
                **kwargs
            )
            
            # Simulate streaming by yielding the complete response
            yield {
                "choices": [{
                    "delta": {
                        "role": "assistant",
                        "content": response["choices"][0]["message"]["content"]
                    },
                    "finish_reason": "stop"
                }],
                "usage": response.get("usage")
            }
            return
        
        raise RuntimeError("No LLM client available for streaming")


# Global LLM client manager
llm_client = LLMClientManager() 
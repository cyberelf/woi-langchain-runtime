"""LangGraph Integration - Simple utilities for LangGraph agent templates.

This module provides utilities for LangGraph-based agent templates.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

from runtime.domain.services.llm.llm_service import LLMService, LLMClient
from runtime.llm.mcp_client import McpLLMClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


class TestChatModel(BaseChatModel):
    """Simple test chat model for testing - no API keys required."""
    
    @property
    def _llm_type(self) -> str:
        return "test"
    
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager = None,
        **kwargs,
    ) -> ChatResult:
        """Generate a test response."""
        test_response = "Test response from mock LLM"
        message = AIMessage(content=test_response)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])


@dataclass
class LLMConfiguration:
    """Simple LLM configuration for testing."""
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 100
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LangGraphLLMService(LLMService):
    """LangGraph LLM Service"""

    async def convert_llm_config_id(self, llm_config_id: str) -> LLMConfiguration:
        """Convert LLM config ID to configuration.
        
        For testing purposes, this provides simple fallback configurations.
        In production, this would look up configurations from a repository.
        """
        # Default configurations for testing
        if llm_config_id == "deepseek" or llm_config_id is None:
            return LLMConfiguration(
                provider="test",  # Use test provider for no API key requirement
                model="test-model",
                temperature=0.1,
                max_tokens=1000,
                metadata={}
            )
        elif llm_config_id == "openai":
            return LLMConfiguration(
                provider="openai", 
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=1000,
                metadata={}
            )
        elif llm_config_id == "google":
            return LLMConfiguration(
                provider="google",
                model="gemini-pro",
                temperature=0.7,
                max_tokens=1000,
                metadata={}
            )
        else:
            # Fallback to test provider for unknown config IDs
            return LLMConfiguration(
                provider="test",
                model="test-model",
                temperature=0.1,
                max_tokens=1000,
                metadata={}
            )

    async def get_client(self, llm_config_id: str):
        """Get the LangGraph LLM client"""
        llm_config = await self.convert_llm_config_id(llm_config_id)
        if llm_config.provider == "openai":
            return ChatOpenAI(
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                **llm_config.metadata
            )
        elif llm_config.provider == "google":
            return ChatGoogleGenerativeAI(
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                **llm_config.metadata
            )
        elif llm_config.provider == "deepseek":
            return ChatDeepSeek(
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                **llm_config.metadata
            )
        elif llm_config.provider == "test":
            # Mock LLM for testing - no API keys required
            return TestChatModel()
        else:
            # Fallback to test provider for unknown providers
            return TestChatModel()


def get_langgraph_llm_service() -> LangGraphLLMService:
    """Get a LangGraph LLM service"""
    return LangGraphLLMService()
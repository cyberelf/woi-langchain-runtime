"""LangGraph Integration - Simple utilities for LangGraph agent templates.

This module provides utilities for LangGraph-based agent templates.
"""

from dataclasses import dataclass
from typing import Any, Optional
import logging

# Removed domain abstraction - using concrete implementation
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatResult, ChatGenerationChunk
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from runtime.settings import settings

from ..config import LLMConfig

logger = logging.getLogger(__name__)

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

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager = None,
        **kwargs,
    ):
        """Stream a test response."""
        test_response = "Test response from mock LLM"
        # Stream the response word by word
        words = test_response.split()
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            message = AIMessageChunk(content=content)
            yield ChatGenerationChunk(message=message)

    def bind_tools(self, tools, **kwargs):
        """Mock implementation of bind_tools for testing.
        
        Returns self to allow the agent to work with tools during testing.
        """
        # Simply return self - tools will be stored but not actually used in test mode
        return self

@dataclass
class LLMConfiguration:
    """Simple LLM configuration for testing."""
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 100
    metadata: Optional[dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LangGraphLLMService:
    """LangGraph LLM Service"""

    def __init__(self, llm_config: Optional[LLMConfig]=None):
        """Initialize with LLM configuration.
        
        Args:
            llm_config: LLMConfig pydantic model or dict (for backward compatibility)
        """
        if llm_config is None:
            # Create default configuration
            self._llm_config = LLMConfig(
                providers={},
                default_provider=None,
                fallback_provider=None
            )
        else:
            # Use pydantic config directly
            self._llm_config = llm_config

    def convert_llm_config_id(self, llm_config_id: Optional[str] = None) -> LLMConfiguration:
        """Convert LLM config ID to configuration using validated config.
        
        Uses the validated LLM configuration provided during initialization.
        """
        # Try to get provider from validated pydantic configuration
        if llm_config_id in self._llm_config.providers:
            provider_config = self._llm_config.providers[llm_config_id]
            return LLMConfiguration(
                provider=provider_config.type,
                model=provider_config.model,
                temperature=provider_config.temperature,
                max_tokens=provider_config.max_tokens,
                metadata=provider_config.metadata
            )
        
        # Try default provider if specified
        default_provider = self._llm_config.default_provider
        if default_provider and default_provider in self._llm_config.providers:
            provider_config = self._llm_config.providers[default_provider]
            return LLMConfiguration(
                provider=provider_config.type,
                model=provider_config.model,
                temperature=provider_config.temperature,
                max_tokens=provider_config.max_tokens,
                metadata=provider_config.metadata
            )
        
        logger.warning(f"No provider found for {llm_config_id}, falling back to test provider")

        # Fallback to test provider
        return LLMConfiguration(
            provider="test",
            model="test-model",
            temperature=0.1,
            max_tokens=1000,
            metadata={}
        )

    def get_client(self, llm_config_id: Optional[str] = None, **execution_params) -> BaseChatModel:
        """Get the LangGraph LLM client with optional execution parameter overrides.
        
        Args:
            llm_config_id: Configuration ID to determine base client settings
            **execution_params: Optional overrides (temperature, max_tokens, etc.)
        """
        llm_config = self.convert_llm_config_id(llm_config_id)
        
        # Override config with execution parameters
        final_temperature = execution_params.get("temperature", llm_config.temperature)
        final_max_tokens = execution_params.get("max_tokens", llm_config.max_tokens)
        
        logger.debug(f"Getting LLM client for {llm_config.provider} with model {llm_config.model}, temperature {final_temperature}, max_tokens {final_max_tokens}, metadata {llm_config.metadata}")

        if llm_config.provider == "openai":
            return ChatOpenAI(
                model=llm_config.model,
                temperature=final_temperature,
                max_completion_tokens=final_max_tokens,
                api_key=settings.openai_api_key,
                **(llm_config.metadata or {})
            )
        elif llm_config.provider == "google":
            return ChatGoogleGenerativeAI(
                model=llm_config.model,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                api_key=settings.google_api_key,
                **(llm_config.metadata or {})
            )
        elif llm_config.provider == "deepseek":
            return ChatDeepSeek(
                model=llm_config.model,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                api_key=settings.deepseek_api_key,
                **(llm_config.metadata or {})
            )
        elif llm_config.provider == "test":
            # Mock LLM for testing - no API keys required
            return TestChatModel()
        else:
            # Fallback to test provider for unknown providers
            return TestChatModel()

    async def shutdown(self) -> None:
        """Shutdown the LLM service."""
        pass


def get_langgraph_llm_service() -> LangGraphLLMService:
    """Get a LangGraph LLM service"""
    return LangGraphLLMService()
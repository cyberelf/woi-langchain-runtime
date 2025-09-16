"""LangGraph Integration - Simple utilities for LangGraph agent templates.

This module provides utilities for LangGraph-based agent templates.
"""

from dataclasses import dataclass
from typing import Any, Optional

from runtime.domain.services.llm import LLMService
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from ..config import LLMConfig
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
    metadata: dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LangGraphLLMService(LLMService):
    """LangGraph LLM Service"""

    def __init__(self, llm_config: Optional[LLMConfig]=None):
        """Initialize with LLM configuration.
        
        Args:
            llm_config: LLMConfig pydantic model or dict (for backward compatibility)
        """
        if llm_config is None:
            # Create default configuration
            self._llm_config = LLMConfig()
        else:
            # Use pydantic config directly
            self._llm_config = llm_config

    async def convert_llm_config_id(self, llm_config_id: str) -> LLMConfiguration:
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
        
        # Fallback to test provider
        return LLMConfiguration(
            provider="test",
            model="test-model",
            temperature=0.1,
            max_tokens=1000,
            metadata={}
        )

    async def get_client(self, llm_config_id: str, **execution_params):
        """Get the LangGraph LLM client with optional execution parameter overrides.
        
        Args:
            llm_config_id: Configuration ID to determine base client settings
            **execution_params: Optional overrides (temperature, max_tokens, etc.)
        """
        llm_config = await self.convert_llm_config_id(llm_config_id)
        
        # Override config with execution parameters
        final_temperature = execution_params.get("temperature", llm_config.temperature)
        final_max_tokens = execution_params.get("max_tokens", llm_config.max_tokens)
        
        if llm_config.provider == "openai":
            return ChatOpenAI(
                model=llm_config.model,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                **llm_config.metadata
            )
        elif llm_config.provider == "google":
            return ChatGoogleGenerativeAI(
                model=llm_config.model,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                **llm_config.metadata
            )
        elif llm_config.provider == "deepseek":
            return ChatDeepSeek(
                model=llm_config.model,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
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
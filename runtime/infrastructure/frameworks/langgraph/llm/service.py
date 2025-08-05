"""LangGraph Integration - Simple utilities for LangGraph agent templates.

This module provides utilities for LangGraph-based agent templates.
"""

from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from ....llm.service import LLMService
from langchain_openai import ChatOpenAI

class LangGraphLLMService(LLMService):
    """LangGraph LLM Service"""

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


def get_langgraph_llm_service() -> LangGraphLLMService:
    """Get a LangGraph LLM service"""
    return LangGraphLLMService()
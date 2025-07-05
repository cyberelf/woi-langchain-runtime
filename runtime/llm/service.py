"""Base Interface for LLM Clients"""

from abc import ABC, abstractmethod
import os
from typing import Any

from runtime.models import LLMConfig

import dotenv
dotenv.load_dotenv()

class LLMService(ABC):
    """Base Interface for LLM Services"""

    @abstractmethod
    async def get_client(self, llm_config_id: str):
        """Get the LLM client"""
        pass

    async def convert_llm_config_id(self, llm_config_id: str) -> LLMConfig:
        """Convert the LLM config id to a configuration"""
        # TODO: Implement this
        if llm_config_id == "deepseek":
            return LLMConfig(
                provider="deepseek",
                model="deepseek-chat",
                temperature=0.7,
                max_tokens=1000,
                metadata={
                    "api_key": os.getenv("DEEPSEEK_API_KEY"),
                },
            )
        elif llm_config_id == "openai":
            return LLMConfig(
                provider="openai",
                model="gpt-4o",
                temperature=0.7,
                max_tokens=1000,
                metadata={
                    "api_key": os.getenv("GOOGLE_API_KEY"),
                },
            )
        elif llm_config_id == "google":
            return LLMConfig(
                provider="google",
                model="gemini-2.5-flash",
                temperature=0.7,
                max_tokens=1000,
                metadata={
                    "api_key": os.getenv("GOOGLE_API_KEY"),
                },
            )
        else:
            raise ValueError(f"Invalid LLM config id: {llm_config_id}")
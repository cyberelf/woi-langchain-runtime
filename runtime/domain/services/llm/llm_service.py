from abc import ABC, abstractmethod

class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    pass

class LLMService(ABC):
    """Abstract base class for LLM services."""

    @abstractmethod
    async def get_client(self, llm_config_id: str) -> LLMClient:
        """Get an LLM client."""
        pass

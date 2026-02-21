"""AI Client Abstraction."""

from abc import ABC, abstractmethod
from typing import Optional


class AIClient(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate content from prompt."""
        pass

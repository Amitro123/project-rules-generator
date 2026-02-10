"""Abstract base class for AI clients."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

class AIClient(ABC):
    """Interface for AI providers."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content from a prompt."""
        pass


class AIClientFactory:
    """Factory to create AI clients based on provider."""

    @staticmethod
    def get_client(provider: str = 'gemini', api_key: Optional[str] = None, model_name: Optional[str] = None) -> AIClient:
        """Get an AI client instance."""

        # Default fallback logic
        if not provider:
            provider = 'gemini'

        if provider == 'groq':
            from src.ai.providers.groq_client import GroqClient
            return GroqClient(api_key=api_key, model_name=model_name)
        elif provider == 'gemini':
            from src.ai.providers.gemini_client import GeminiClient
            return GeminiClient(api_key=api_key, model_name=model_name)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

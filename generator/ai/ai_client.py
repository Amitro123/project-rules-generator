"""AI Client Abstraction."""
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class AIClient(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 2000, model: Optional[str] = None, temperature: float = 0.7) -> str:
        """Generate content from prompt."""
        pass

def create_ai_client(provider: str = 'groq', **kwargs) -> AIClient:
    """Factory to create AI client instance."""
    
    if provider == 'groq':
        from .providers.groq_client import GroqClient
        return GroqClient(**kwargs)
    elif provider == 'gemini':
        from .providers.gemini_client import GeminiClient
        return GeminiClient(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")

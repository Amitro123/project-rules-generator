"""AI Client Factory."""

from typing import Any

from .ai_client import AIClient


def create_ai_client(provider: str = "groq", **kwargs: Any) -> AIClient:
    """Factory to create AI client instance."""
    
    if provider == "groq":
        from .providers.groq_client import GroqClient
        return GroqClient(**kwargs)
    elif provider == "gemini":
        from .providers.gemini_client import GeminiClient
        return GeminiClient(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")

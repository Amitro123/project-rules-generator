"""AI Client Factory."""

from typing import Any

from .ai_client import AIClient

SUPPORTED_PROVIDERS = ("groq", "gemini", "anthropic", "openai")


def create_ai_client(provider: str = "groq", **kwargs: Any) -> AIClient:
    """Factory to create AI client instance.

    Args:
        provider: One of "groq", "gemini", "anthropic", "openai"
        **kwargs: Passed to the client constructor (e.g. api_key=...)

    Raises:
        ValueError: If provider is not recognised.
    """
    if provider == "groq":
        from .providers.groq_client import GroqClient

        return GroqClient(**kwargs)
    elif provider == "gemini":
        from .providers.gemini_client import GeminiClient

        return GeminiClient(**kwargs)
    elif provider == "anthropic":
        from .providers.anthropic_client import AnthropicClient

        return AnthropicClient(**kwargs)
    elif provider == "openai":
        from .providers.openai_client import OpenAIClient

        return OpenAIClient(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider: {provider!r}. " f"Supported: {', '.join(SUPPORTED_PROVIDERS)}")

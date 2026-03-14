"""Shared CLI utilities."""

import os


def detect_provider(provider: str | None, api_key: str | None) -> str:
    """Auto-detect AI provider from api_key prefix or environment variables.

    Priority:
    1. Explicit --provider flag (returned as-is).
    2. api_key prefix  (gsk_ → groq, sk-ant- → anthropic, sk- → openai).
    3. Environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY).
    4. Default: groq.
    """
    if provider is not None:
        return provider
    if api_key:
        if api_key.startswith("gsk_"):
            return "groq"
        if api_key.startswith("sk-ant-"):
            return "anthropic"
        if api_key.startswith("sk-"):
            return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GROQ_API_KEY"):
        return "gemini"
    return "groq"


def set_api_key_env(provider: str, api_key: str | None) -> None:
    """Set the correct environment variable for the given provider."""
    if not api_key:
        return
    env_map = {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var:
        os.environ[env_var] = api_key

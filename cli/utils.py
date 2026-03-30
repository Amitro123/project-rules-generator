"""Shared CLI utilities."""

import os
from typing import Optional


def detect_provider(provider: Optional[str], api_key: Optional[str]) -> str:
    """Auto-detect AI provider from api_key prefix or environment variables.

    Priority:
    1. Explicit --provider flag (returned as-is).
    2. api_key prefix  (gsk_ → groq, sk-ant- → anthropic, sk- → openai).
    3. Environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY).
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
    _gemini_available = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if _gemini_available and not os.environ.get("GROQ_API_KEY"):
        return "gemini"
    return "groq"


def set_api_key_env(provider: str, api_key: Optional[str]) -> None:
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

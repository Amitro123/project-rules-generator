"""Shared CLI utilities."""

import os
from typing import Optional


def detect_provider(provider: Optional[str], api_key: Optional[str]) -> Optional[str]:
    """Auto-detect AI provider from api_key prefix or environment variables.

    Priority:
    1. Explicit --provider flag (returned as-is).
    2. api_key prefix  (gsk_ → groq, sk-ant- → anthropic, sk- → openai).
    3. Environment variables (GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY).
    4. Returns None if no key is found — callers must check for None and fail gracefully.
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
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return None


def has_api_key(provider: Optional[str], api_key: Optional[str]) -> bool:
    """Return True if a usable API key exists for the given provider.

    Checks the passed api_key first, then the relevant environment variable(s).
    Returns False when provider is None or no key can be found.
    """
    if api_key:
        return True
    if not provider:
        return False
    _env_keys = {
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
    }
    return any(os.environ.get(k) for k in _env_keys.get(provider, []))


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

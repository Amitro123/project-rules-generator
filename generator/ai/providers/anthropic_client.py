"""Anthropic/Claude AI Provider."""

import os
from typing import Optional

from ...utils.encoding import normalize_mojibake
from ..ai_client import AIClient

try:
    import anthropic as _anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    _anthropic = None
    ANTHROPIC_AVAILABLE = False


class AnthropicClient(AIClient):
    """Anthropic Claude API client."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    DEFAULT_TIMEOUT = 60.0  # seconds

    def __init__(self, api_key: Optional[str] = None):
        if _anthropic is None:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"))
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found.")

        self.client = _anthropic.Anthropic(api_key=self.api_key, timeout=self.DEFAULT_TIMEOUT)

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate content using Anthropic Claude."""
        try:
            msg = self.client.messages.create(
                model=model or os.getenv("ANTHROPIC_MODEL", self.DEFAULT_MODEL),
                max_tokens=max_tokens,
                system=system_message or "You are an expert AI skill generator for developer tools.",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            raw = next((b.text for b in msg.content if hasattr(b, "text")), "") if msg.content else ""
            return normalize_mojibake(raw)
        except Exception as e:  # noqa: BLE001 — Anthropic SDK raises diverse provider errors
            raise RuntimeError(f"Anthropic generation failed: {e}") from e

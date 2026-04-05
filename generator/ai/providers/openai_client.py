"""OpenAI API Provider."""

import os
from typing import Optional

from ...utils.encoding import normalize_mojibake
from ..ai_client import AIClient

try:
    from openai import OpenAI as _OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    _OpenAI = None
    OPENAI_AVAILABLE = False


class OpenAIClient(AIClient):
    """OpenAI API client (GPT-4o / GPT-4o-mini)."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: Optional[str] = None):
        if _OpenAI is None:
            raise ImportError("openai package not installed. Run: pip install openai")

        super().__init__(api_key or os.getenv("OPENAI_API_KEY"))
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found.")

        self.client = _OpenAI(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate content using OpenAI."""
        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            resp = self.client.chat.completions.create(
                model=model or os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL),
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            raw = resp.choices[0].message.content or ""
            return normalize_mojibake(raw)
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {e}") from e

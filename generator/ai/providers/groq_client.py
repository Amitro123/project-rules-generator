"""Groq AI Provider."""

import os
from typing import Optional

from ...utils.encoding import normalize_mojibake
from ..ai_client import AIClient

try:
    from groq import Groq

    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class GroqClient(AIClient):
    """Groq API client."""

    DEFAULT_MODEL = "llama-3.1-8b-instant"

    def __init__(self, api_key: Optional[str] = None):
        if not GROQ_AVAILABLE:
            raise ImportError("groq package not installed. Run: pip install groq")

        super().__init__(api_key or os.getenv("GROQ_API_KEY"))
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found.")

        self.client = Groq(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate content using Groq."""
        try:
            messages: list = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            completion = self.client.chat.completions.create(
                model=model or self.DEFAULT_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # Clean encoding artifacts per AMIT_CODING_PREFERENCES.md
            return normalize_mojibake(completion.choices[0].message.content or "")
        except Exception as e:
            raise RuntimeError(f"Groq generation failed: {e}")

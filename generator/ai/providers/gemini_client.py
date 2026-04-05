"""Gemini AI Provider."""

import os
from typing import Optional

from ...utils.encoding import normalize_mojibake
from ..ai_client import AIClient

try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except ImportError:
    import types as _stdlib_types

    genai = _stdlib_types.SimpleNamespace(Client=None)
    types = _stdlib_types.SimpleNamespace(GenerateContentConfig=lambda **kwargs: None)
    GEMINI_AVAILABLE = False


class GeminiClient(AIClient):
    """Google Gemini API client."""

    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_TIMEOUT = 60  # seconds (Gemini http_options accepts int seconds)

    def __init__(self, api_key: Optional[str] = None):
        if getattr(genai, "Client", None) is None:
            raise ImportError("google-genai not installed. Run: pip install google-genai")

        super().__init__(api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found.")

        self.client = genai.Client(api_key=self.api_key, http_options={"timeout": self.DEFAULT_TIMEOUT})

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate content using Gemini."""
        try:
            full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt
            response = self.client.models.generate_content(
                model=model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL) or self.DEFAULT_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            # Clean encoding artifacts per AMIT_CODING_PREFERENCES.md
            return normalize_mojibake(response.text or "")
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {e}") from e

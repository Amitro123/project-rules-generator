"""Gemini AI Provider."""
import os
from typing import Optional
from ..ai_client import AIClient
from ...utils.encoding import normalize_mojibake

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class GeminiClient(AIClient):
    """Google Gemini API client."""
    
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: Optional[str] = None):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
            
        super().__init__(api_key or os.getenv("GEMINI_API_KEY"))
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found.")
            
        self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, max_tokens: int = 2000, model: Optional[str] = None, temperature: float = 0.7) -> str:
        """Generate content using Gemini."""
        try:
            response = self.client.models.generate_content(
                model=model or os.getenv('GEMINI_MODEL', self.DEFAULT_MODEL),
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            # Clean encoding artifacts per AMIT_CODING_PREFERENCES.md
            return normalize_mojibake(response.text)
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {e}")

"""Groq AI Client Implementation."""

import logging
import os
from typing import Optional

from src.ai.ai_client import AIClient

logger = logging.getLogger(__name__)


class GroqClient(AIClient):
    """Client for Groq AI API."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(
            api_key=api_key or os.getenv("GROQ_API_KEY"),
            model_name=model_name or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        )

    def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content using Groq."""
        if not self.api_key:
            logger.warning("Groq API key not found. Skipping generation.")
            return ""

        try:
            from groq import Groq

            client = Groq(api_key=self.api_key)

            # Groq uses 'messages' format
            messages = [{"role": "user", "content": prompt}]

            temperature = kwargs.get("temperature", 0.5)
            max_tokens = kwargs.get(
                "max_tokens", 4096
            )  # Groq allows larger context on some models

            chat_completion = client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = chat_completion.choices[0].message.content or ""

            # Clean encoding artifacts
            # Fix Windows/Terminal encoding issues where em-dash appears as garbage
            content = content.encode("utf-8", errors="replace").decode("utf-8")
            content = content.replace("ג€”", "—").replace("ג", "")

            return content.strip()
        except ImportError:
            logger.error("groq package not installed.")
            return ""
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return ""

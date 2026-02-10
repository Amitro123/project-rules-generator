"""Gemini AI Client Implementation."""

import os
from typing import Optional, Dict, Any
from src.ai.ai_client import AIClient
import logging

logger = logging.getLogger(__name__)

class GeminiClient(AIClient):
    """Client for Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(api_key=api_key or os.getenv('GEMINI_API_KEY'), model_name=model_name or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'))

    def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content using Gemini."""
        if not self.api_key:
            logger.warning("Gemini API key not found. Skipping generation.")
            return ''

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Allow kwargs to override defaults
            temperature = kwargs.get('temperature', 0.4)
            max_tokens = kwargs.get('max_tokens', 3000)

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            text = response.text if response.text else ''
            
            # Clean encoding artifacts
            # Fix Windows/Terminal encoding issues where em-dash appears as garbage
            text = text.encode('utf-8', errors='replace').decode('utf-8')
            text = text.replace('ג€”', '—').replace('ג', '')
            
            return text.strip()
        except ImportError:
            logger.error("google-generativeai package not installed.")
            return ''
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return ''


import pytest
from unittest.mock import MagicMock, patch
import os
from generator.ai.providers.gemini_client import GeminiClient
from generator.ai.providers.groq_client import GroqClient

class TestEncodingFix:
    def test_gemini_client_encoding_fix(self):
        """Test that GeminiClient cleans encoding artifacts."""
        with patch('google.genai.Client') as MockClient:
            # Setup mock
            mock_instance = MockClient.return_value
            mock_response = MagicMock()
            # Corrupted string: "Some content ג€” with artifacts ג"
            mock_response.text = "Some content ג€” with artifacts ג"
            mock_instance.models.generate_content.return_value = mock_response
            
            client = GeminiClient(api_key="dummy")
            result = client.generate("test prompt")
            
            # Assert artifacts are removed and replaced correctly
            assert result == "Some content — with artifacts"
            assert "ג€”" not in result
            assert "ג" not in result

    def test_groq_client_encoding_fix(self):
        """Test that GroqClient cleans encoding artifacts."""
        with patch('groq.Groq') as MockGroq:
            # Setup mock
            mock_instance = MockGroq.return_value
            mock_chat_completion = MagicMock()
            mock_message = MagicMock()
            mock_message.content = "Groq content ג€” with artifacts ג"
            mock_chat_completion.choices = [MagicMock(message=mock_message)]
            
            mock_instance.chat.completions.create.return_value = mock_chat_completion
            
            client = GroqClient(api_key="dummy")
            result = client.generate("test prompt")
            
            # Assert artifacts are removed and replaced correctly
            assert result == "Groq content — with artifacts"
            assert "ג€”" not in result
            assert "ג" not in result

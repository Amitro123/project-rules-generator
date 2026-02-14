from unittest.mock import MagicMock, patch

from generator.ai.providers.gemini_client import GeminiClient
from generator.ai.providers.groq_client import GroqClient


class TestEncodingFix:
    def test_gemini_client_encoding_fix(self):
        """Test that GeminiClient cleans encoding artifacts."""
        # Patch where genai is imported in gemini_client.py
        with patch("generator.ai.providers.gemini_client.genai.Client") as MockClient:
            # Setup mock
            mock_instance = MockClient.return_value
            mock_response = MagicMock()
            # Corrupted string with mojibake
            mock_response.text = "Some content \u05d2\u20ac\u201d with artifacts \u05d2"
            mock_instance.models.generate_content.return_value = mock_response

            client = GeminiClient(api_key="dummy")
            result = client.generate("test prompt")

            # Assert mojibake is replaced with em-dash, legitimate Hebrew preserved
            assert result == "Some content \u2014 with artifacts \u05d2"
            assert "\u05d2\u20ac\u201d" not in result  # Mojibake removed
            assert "\u2014" in result  # Replaced with correct character

    def test_groq_client_encoding_fix(self):
        """Test that GroqClient cleans encoding artifacts."""
        # Patch where Groq is imported in groq_client.py
        with patch("generator.ai.providers.groq_client.Groq") as MockGroq:
            # Setup mock
            mock_instance = MockGroq.return_value
            mock_chat_completion = MagicMock()
            mock_message = MagicMock()
            mock_message.content = (
                "Groq content \u05d2\u20ac\u201d with artifacts \u05d2"
            )
            mock_chat_completion.choices = [MagicMock(message=mock_message)]

            mock_instance.chat.completions.create.return_value = mock_chat_completion

            client = GroqClient(api_key="dummy")
            result = client.generate("test prompt")

            # Assert mojibake is replaced with em-dash, legitimate Hebrew preserved
            assert result == "Groq content \u2014 with artifacts \u05d2"
            assert "\u05d2\u20ac\u201d" not in result  # Mojibake removed
            assert "\u2014" in result  # Replaced with correct character

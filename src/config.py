from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables or a .env file.
    This class defines the configuration for various API keys used by the application.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="API key for OpenAI services (e.g., GPT models)."
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        env="ANTHROPIC_API_KEY",
        description="API key for Anthropic services (e.g., Claude models)."
    )
    google_api_key: Optional[str] = Field(
        default=None,
        env="GOOGLE_API_KEY",
        description="API key for Google services (e.g., Gemini models)."
    )
    groq_api_key: Optional[str] = Field(
        default=None,
        env="GROQ_API_KEY",
        description="API key for Groq services."
    )

# Instantiate settings for easy access throughout the application
settings = Settings()
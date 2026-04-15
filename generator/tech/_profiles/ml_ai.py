"""ML / AI TechProfile entries."""

from typing import List

from generator.tech.profile import TechProfile

ML_AI: List[TechProfile] = [
    TechProfile(
        name="pytorch",
        display_name="PyTorch",
        category="ml",
        skill_name="pytorch-training",
        packages=["torch"],
        readme_keywords=["pytorch", "torch"],
    ),
    TechProfile(
        name="tensorflow",
        display_name="TensorFlow",
        category="ml",
        skill_name="tensorflow-models",
        packages=["tensorflow"],
        readme_keywords=["tensorflow"],
    ),
    TechProfile(
        name="openai",
        display_name="OpenAI",
        category="ai",
        skill_name="openai-api",
        packages=["openai"],
        readme_keywords=["openai", "gpt-4", "gpt-3"],
        tools=["pytest", "ruff", "mypy"],
    ),
    TechProfile(
        name="anthropic",
        display_name="Anthropic",
        category="ai",
        skill_name="claude-cowork-workflow",
        packages=["anthropic"],
        readme_keywords=["anthropic", "claude"],
        tools=["pytest", "ruff", "mypy"],
    ),
    TechProfile(
        name="groq",
        display_name="Groq",
        category="ai",
        skill_name="groq-api",
        packages=["groq"],
        readme_keywords=["groq"],
        tools=["pytest", "ruff", "mypy"],
        rules={
            "high": [
                "Always use the GroqClient wrapper — never call the Groq API directly",
                "Set GROQ_API_KEY via environment variable, never hardcode",
                "Handle groq.RateLimitError with exponential backoff retry",
            ],
            "medium": [
                "Use llama-3.1-8b-instant for fast tasks, llama-3.3-70b for quality",
                "Log token usage per request for cost monitoring",
                "Implement provider fallback: Groq -> Gemini on failure",
            ],
        },
    ),
    TechProfile(
        name="gemini",
        display_name="Gemini",
        category="ai",
        skill_name="gemini-api",
        packages=["google-generativeai", "google-genai"],
        readme_keywords=["gemini", "google ai"],
        import_name="google",
        tools=["pytest", "ruff", "mypy"],
        rules={
            "high": [
                "Always use the GeminiClient wrapper — never call the Gemini API directly",
                "Set GEMINI_API_KEY via environment variable, never hardcode",
                "Handle google.api_core.exceptions.ResourceExhausted with retry",
            ],
            "medium": [
                "Use gemini-2.0-flash for speed, gemini-1.5-pro for complex reasoning",
                "Implement provider fallback: Gemini -> Groq on quota exhaustion",
                "Log model name and token count for every API call",
            ],
        },
    ),
    TechProfile(
        name="perplexity",
        display_name="Perplexity",
        category="ai",
        skill_name="perplexity-api",
        packages=["perplexity"],
        readme_keywords=["perplexity", "sonar"],
    ),
    TechProfile(
        name="langchain",
        display_name="LangChain",
        category="ai",
        skill_name="langchain-chains",
        packages=["langchain"],
        readme_keywords=["langchain"],
        tools=["pytest", "ruff"],
    ),
]

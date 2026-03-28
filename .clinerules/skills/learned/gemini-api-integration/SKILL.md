---
name: gemini-api-integration
description: |
  Best practices and patterns for integrating the Gemini API in a Python project, focusing on configuration, secure key management, and structured API calls.
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  tags: [gemini, api, integration, python, security, best-practices]
---

# Skill: Gemini API Integration

## Purpose

This skill provides guidance on securely and effectively integrating the Gemini API into this Python project. Given the project's Python tech stack and the need for external API interaction, establishing clear patterns for configuration, API client setup, and robust error handling is crucial to ensure maintainability and security.

## Auto-Trigger

Activate when the user mentions:
- **"integrate gemini api"**
- **"gemini api key"**
- **"how to use gemini model"**

Do NOT activate for: gemini constellation, gemini zodiac, gemini twins

## CRITICAL

- Always secure your Gemini API key. Never hardcode it directly in source code.
- Implement robust error handling for all API calls to gracefully manage network issues, rate limits, or API-specific errors.

## Process

### 1. Secure API Key Configuration

Ensure your Gemini API key is managed securely, preferably using environment variables. This prevents sensitive information from being committed to version control.

```bash
echo "Set your Gemini API key as an environment variable:"
echo 'export GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"'
echo "You can add this to your shell profile (e.g., ~/.bashrc, ~/.zshrc) or pass it directly when running your application."
```

### 2. Install Gemini Python Client Library

If not already present in `requirements.txt` or `pyproject.toml`, ensure the official Google Generative AI client library is installed.

```bash
pip install google-generativeai
```

### 3. Implement a Dedicated API Client Module

Create a dedicated Python module (e.g., in an `api` directory if applicable, or a new file like `gemini_client.py`) to encapsulate Gemini API interactions. This improves modularity and testability.

### 4. Make API Calls with Error Handling

Structure your API calls to include proper error handling. This is vital for a resilient application.

### 5. Validate Integration

After implementing the integration, run a simple test to ensure the API calls are working as expected and the key is being loaded correctly. This project has tests, so consider adding a dedicated integration test.

```bash
# Example: Run a simple Python script to test connectivity
python -c "import os; import google.generativeai as genai; genai.configure(api_key=os.getenv('GEMINI_API_KEY')); model = genai.GenerativeModel('gemini-pro'); response = model.generate_content('Hello, Gemini!'); print(response.text if response else 'No response')"
```

## Output

- A more secure method for handling the Gemini API key.
- A well-structured and modular approach to interacting with the Gemini API.
- Code examples demonstrating best practices for API client initialization and API calls with error handling.

## Anti-Patterns

❌ **Don't** Hardcode your `GEMINI_API_KEY` directly into `main.py` or any other source file.
✅ **Do** Load your `GEMINI_API_KEY` from environment variables using `os.getenv()`.

❌ **Don't** Make raw API calls directly within application logic without wrapping them in `try...except` blocks.
✅ **Do** Encapsulate API calls within a dedicated function or class method, including comprehensive error handling for network issues, API errors, and rate limits.

## Examples

```python
# Example: Securely loading API key and initializing Gemini client
import os
import google.generativeai as genai

def get_gemini_client():
    """
    Configures and returns the Gemini GenerativeModel client.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-pro')

def generate_content_with_gemini(prompt: str) -> str:
    """
    Makes a content generation request to the Gemini API with error handling.
    """
    try:
        model = get_gemini_client()
        response = model.generate_content(prompt)
        # Check if response exists and has text
        if response and response.text:
            return response.text
        else:
            print(f"Gemini API returned an empty or invalid response for prompt: {prompt}")
            return "Error: Could not generate content."
    except ValueError as e:
        print(f"Configuration error: {e}")
        return "Error: API key not configured."
    except Exception as e:
        print(f"An unexpected error occurred during Gemini API call: {e}")
        # In a real application, you might log the full exception details
        return "Error: Failed to communicate with Gemini API."

# Example usage (e.g., in main.py or an API endpoint)
if __name__ == "__main__":
    test_prompt = "Tell me a short, inspiring story."
    generated_text = generate_content_with_gemini(test_prompt)
    print(f"\n--- Generated Content ---")
    print(generated_text)
```
# Design: Authentication System for Python CLI

## Problem Statement
The current Python CLI lacks a robust authentication system, preventing secure access to external LLM APIs (OpenAI, Anthropic, Groq, etc.) and user-specific configuration. This omission leads to hardcoded API keys, insecure management practices, and an inability to personalize or restrict command usage, hindering the project's scalability and security posture for a multi-user or multi-API environment.

## Architecture Decisions

- **Authentication Mechanism**: API Key/Token-based Authentication (vs OAuth2, Username/Password)
- **Secret Storage Strategy**: Environment Variables (primary) with Encrypted Local File (secondary) (vs Plaintext Local File, OS Keyring)
- **Integration Pattern for Commands**: Click Decorator for Authentication (vs Manual Checks, Middleware)

## API Contracts

- `ctx`: `click.Context` - The current Click context object, used to store and retrieve shared data.
- `AuthError`: If an encryption key is required for local file access but not provided.
- `CryptoError`: If there's an issue with encryption/decryption of the local file.
- `provider`: `str` - The name of the LLM provider (e.g., "openai", "anthropic", "groq").
- `key`: `str` - The API key for the specified provider.
- `AuthError`: If the `MYCLI_ENCRYPTION_KEY` environment variable is not set, preventing local file encryption.
- `ValueError`: If `provider` is not a recognized LLM provider.

## Success Criteria

- **Security**: API keys for external services are never stored in plaintext on disk or committed to version control. (`MYCLI_ENCRYPTION_KEY` is mandatory for local storage).
- **Usability**: Users can configure API keys via environment variables or a dedicated `mycli auth configure` command.
- **Reliability**: Authentication failures (e.g., missing API key, decryption error) are gracefully handled, providing clear and actionable error messages to the user, without crashing the CLI.
- **Maintainability**: The authentication logic is modular, encapsulated within `auth_manager.py` and `auth_models.py`, and reusable across all authenticated commands via a Click decorator.
- **Test Coverage**: Unit test coverage for all `auth` module components (`AuthSettings`, `AuthManager`, encryption utilities) exceeds 90%.

---
name: config-management
description: |
  Developers struggle with inconsistent and error-prone configuration handling; this skill standardizes configuration loading, validation, and access using Pydantic and YAML for robust application behavior.
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  tags: [configuration, pydantic, yaml, cli, best-practices]
---

# Skill: Config Management

## Purpose

Every time you introduce a new setting or modify an existing one without a standardized approach, you risk runtime errors, inconsistent application behavior, and difficult-to-debug issues. The common mistake is to scatter configuration parsing and validation logic throughout the codebase or to rely on untyped dictionaries, leading to brittle code. This skill establishes a robust, type-safe, and centralized configuration management workflow using Pydantic for validation and YAML for storage, ensuring all application settings are correctly structured, validated, and easily accessible, preventing unexpected failures and improving maintainability.

## Auto-Trigger

Activate when the user mentions:
- **"manage config"**
- **"update configuration"**
- **"config settings"**

Do NOT activate for: git config, database config

## CRITICAL

- Configuration MUST be defined using Pydantic schemas for type safety and validation.
- All application configuration MUST be loaded from `config.yaml` or environment variables, not hardcoded.
- Configuration loading and validation MUST be centralized in a dedicated module to ensure consistency across the application.

## Process

### 1. Define Configuration Schema

Defining a Pydantic schema ensures all configuration values adhere to expected types and structures, preventing common data-related bugs before they manifest at runtime.

```python
# File: prg_utils/config_schema.py (example from project)
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr, Field

class LLMConfig(BaseModel):
    enabled: bool = True
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000

class GitConfig(BaseModel):
    auto_commit: bool = True
    commit_message: str = "feat: Automated skill generation"
    commit_user_name: str = "PRG Bot"
    commit_user_email: EmailStr = "prg-bot@example.com"
    target_branch: str = "main"

class GenerationConfig(BaseModel):
    output_dir: str = "_bmad-output"
    strategy: str = "default"

class RootConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)

def validate_config(config_dict: Dict) -> RootConfig:
    """Validate and normalize configuration dictionary."""
    return RootConfig(**config_dict)
```

### 2. Centralize Configuration Loading

Consolidating configuration loading into a single function ensures that all parts of the application retrieve settings from the same source and undergo the same validation process, promoting consistency.

```python
# File: cli/analyze_cmd.py (example from project)
import yaml
from pathlib import Path
from prg_utils.config_schema import validate_config # Assuming this import path based on context

def load_config():
    """Load configuration from config.yaml."""
    # Adjusted path for refactor module
    config_path = Path(__file__).parent.parent / "config.yaml"
    raw_config = {}
    if config_path.exists():
        raw_config = yaml.safe_load(config_path.read_text()) or {}

    # Validate and fill defaults
    config_model = validate_config(raw_config)
    return config_model.model_dump() # Return as dict for existing usage if needed, or the Pydantic object
```

### 3. Validate Configuration with Tests

Regularly running tests that specifically cover configuration loading and validation ensures that changes to the `config.yaml` or schema do not introduce silent failures, catching issues early in the development cycle.

```bash
# Run specific tests that validate config loading and defaults
pytest tests/test_cli.py::TestConfig::test_load_config_default
```

## Output

- A consistent, type-safe `RootConfig` Pydantic object (or its dictionary representation) containing all validated application settings.
- Increased confidence that configuration is correctly parsed and applied.

## Anti-Patterns

❌ **Don't** manually parse configuration values in different modules without Pydantic validation. This leads to inconsistent data types and missing validation, causing runtime errors that are hard to trace.
✅ **Do** always use the
### pydantic-model-defaults
Ensuring consistent default values and configurations for Pydantic models in this project.

**Context:** This project heavily relies on Pydantic models for configuration and data validation, as evidenced by the `prg_utils/config_schema.py` file. Consistent default values are crucial for predictable behavior and avoiding unexpected errors.

**When to use:**
- Defining new configuration options.
- Refactoring existing configurations.
- Debugging unexpected behavior related to configuration settings.

**Check for:**
1. Missing default values in Pydantic models leading to `None` values where a default is expected. This can cause errors if the code expects a specific type.
2. Inconsistent naming conventions for configuration options across different models.

**Good pattern (from this project):**
```python
# File: prg_utils/config_schema.py
class LLMConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None
    provider: Literal["anthropic", "gemini"] = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
```

**Anti-pattern to fix:**
```python
# File: prg_utils/config_schema.py
class SkillSourceConfig(BaseModel):
    enabled: bool = True
    path: Optional[str] = None # Potential issue: No default path provided, might lead to None errors.
    auto_save: bool = False
```

**Action items:**
1. Add a default value for `path` in `SkillSourceConfig` within `prg_utils/config_schema.py` to prevent potential `None` errors if a path is not explicitly provided. Suggestion: `path: str = ""`
2. Review all Pydantic models in `prg_utils/config_schema.py` and ensure consistent naming conventions for similar configuration options. For example, use consistent casing (snake_case or camelCase) for all option names.

### pydantic-model-patterns
Consistent and validated data structures using Pydantic models.

**Context:** This project heavily relies on Pydantic models for configuration, data validation, and API request/response structures. Maintaining consistency and correctness in these models is crucial for the application's stability.

**When to use:**
- Defining configuration schemas (e.g., for LLM, Git, or skill generation)
- Representing data structures for internal processing
- Defining the structure of data for API endpoints (if FastAPI were used more extensively).

**Check for:**
1. Missing type annotations or default values in Pydantic models, leading to potential runtime errors. Example: `my_field: str` should ideally be `my_field: str = ""` or `my_field: Optional[str] = None`
2. Inconsistent naming conventions across different Pydantic models.

**Good pattern (from this project):**
```python
# File: prg_utils\config_schema.py
class LLMConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None
    provider: Literal["anthropic", "gemini"] = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
```

**Anti-pattern to fix:**
```python
# File: prg_utils\config_schema.py (Hypothetical - there isn't a direct anti-pattern currently, but demonstrates the point)
class InconsistentConfig(BaseModel):
    is_active = True  # Inconsistent naming (snake_case vs camelCase)
    path: str # Missing default value, and not Optional.
```

**Action items:**
1. Review all Pydantic models in `prg_utils/config_schema.py` for consistent naming conventions (snake_case) and appropriate default values or `Optional` types for all fields.
2. Add tests to `tests/test_config_schema.py` to validate the structure and default values of the Pydantic models.  Specifically, ensure the default values match the expected application behavior.

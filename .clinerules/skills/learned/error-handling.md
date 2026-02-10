### pydantic-model-validation
Leverage Pydantic's validation features for robust data handling in configuration models.

**Context:** This project heavily relies on Pydantic's `BaseModel` for configuration management (e.g., `LLMConfig`, `GitConfig`, `GenerationConfig` in `prg_utils/config_schema.py`).  Proper validation ensures that these configurations are valid before being used, preventing unexpected behavior.

**When to use:**
- Defining new configuration classes using `BaseModel`.
- Modifying existing configuration classes to add new fields or constraints.

**Check for:**
1. Missing type annotations in `BaseModel` classes, leading to runtime errors instead of validation errors.
   ```python
   # Anti-pattern
   class MyConfig(BaseModel):
       my_value  # Missing type annotation
   ```
2. Lack of validation constraints (e.g., `ge`, `le`, `Literal`) on fields where specific values or ranges are required.  This can result in invalid configurations being loaded.

**Good pattern (from this project):**
```python
# File: prg_utils/config_schema.py
class GenerationConfig(BaseModel):
    output_format: Literal["markdown", "json", "yaml"] = "markdown"
    max_feature_count: int = Field(default=5, ge=1, le=20)
    max_description_length: int = Field(default=200, ge=50, le=1000)
```

**Anti-pattern to fix:**
```python
# File: prg_utils/config_schema.py (hypothetical example)
class BadConfig(BaseModel):
    api_url: str  # No validation to ensure it's a valid URL
    retries: int  # No validation to ensure it's a positive integer
```

**Action items:**
1. Add URL validation to `api_url` field in any relevant config classes using `pydantic.HttpUrl`.
2. Add `ge=0` validation to `retries` field in any relevant config classes to ensure it's non-negative.
3. Add pytest to validate config classes using `pytest.raises(ValidationError)` to ensure appropriate errors are raised for invalid configurations. For example, create a test case in `tests/test_config_schema.py` that attempts to instantiate `GenerationConfig` with `max_feature_count=0` and asserts that a `ValidationError` is raised.

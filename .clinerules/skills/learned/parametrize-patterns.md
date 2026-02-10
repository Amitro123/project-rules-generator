### pydantic-model-definitions
Consistent and maintainable Pydantic model definitions for configuration and data structures.

**Context:** This project heavily relies on Pydantic models (inheriting from `BaseModel`) for defining configuration schemas (e.g., `LLMConfig`, `GitConfig`, `GenerationConfig` in `prg_utils/config_schema.py`) and potentially other data structures. Consistent use of features like default values, field validation, and optional types improves code readability and reduces errors.

**When to use:**
- Defining new configuration settings.
- Representing data structures received from or sent to external APIs.
- Defining the structure of skills and rules.

**Check for:**
1.  Inconsistent use of `Optional[Type]` vs. `Type = None` for optional fields.  While both achieve the same result, using `Optional[Type]` is generally preferred for clarity.
2.  Missing field validation using `Field` with `ge`, `le`, `gt`, `lt`, `min_length`, `max_length` where appropriate.  Failing to validate input can lead to unexpected behavior and security vulnerabilities.

**Good pattern (from this project):**
```python
# File: prg_utils/config_schema.py
class GenerationConfig(BaseModel):
    output_format: Literal["markdown", "json", "yaml"] = "markdown"
    include_examples: bool = True
    verbose: bool = True
    max_feature_count: int = Field(default=5, ge=1, le=20)
    max_description_length: int = Field(default=200, ge=50, le=1000)
```

**Anti-pattern to fix:**
```python
# File: prg_utils/config_schema.py (hypothetical - example of missing validation)
class ExampleConfig(BaseModel):
    port: int  # Missing validation - could be negative or too large
```

**Action items:**
1.  Review all Pydantic models and add appropriate field validation using `Field` where necessary (all files under `prg_utils/config_schema.py` and any other files defining Pydantic models).
2.  Add unit tests to specifically test the validation logic of Pydantic models, ensuring that invalid values are rejected and valid values are accepted (create or modify tests in `tests/`).

### pydantic-model-validation
Ensuring robust data validation and type safety using Pydantic models within the project.

**Context:** This project heavily relies on Pydantic models for configuration, data serialization, and API request/response validation. Correctly defined and validated models are crucial for preventing runtime errors and ensuring data integrity throughout the application.

**When to use:**
- Defining new configuration schemas (e.g., for LLM providers or git settings)
- Handling API requests and responses in FastAPI endpoints
- Processing external data sources

**Check for:**
1. Missing type annotations or incorrect type hints in Pydantic models, leading to potential validation issues. For example, using `str` instead of `Optional[str]` when a field can be null.
2. Lack of field validation using `Field` with appropriate constraints (e.g., `ge`, `le`, `regex`) to enforce data integrity.

**Good pattern (from this project):**
```python
# File: prg_utils\config_schema.py
class GenerationConfig(BaseModel):
    output_format: Literal["markdown", "json", "yaml"] = "markdown"
    include_examples: bool = True
    verbose: bool = True
    max_feature_count: int = Field(default=5, ge=1, le=20)
    max_description_length: int = Field(default=200, ge=50, le=1000)
```

**Anti-pattern to fix:**
```python
# File: prg_utils\config_schema.py (Hypothetical - assuming a missing validation)
class BadConfig(BaseModel):
    name: str  # Missing validation - could be empty or too long
    age: int  # Missing validation - could be negative
```

**Action items:**
1. Review all Pydantic models in `prg_utils\config_schema.py` and ensure all fields have appropriate type annotations and validation constraints using `Field`. Specifically, check if all optional fields use `Optional[Type]` and if numerical/string fields have appropriate `ge`, `le`, `min_length`, `max_length`, or `regex` constraints.
2. Add unit tests using pytest to validate that Pydantic models correctly enforce the defined constraints. For example, create tests that attempt to instantiate models with invalid data and assert that `ValidationError` is raised.

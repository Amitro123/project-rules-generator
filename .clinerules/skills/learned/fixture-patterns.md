### pydantic-model-inheritance
Consistent use of Pydantic's BaseModel for configuration and data structures, ensuring type safety and validation.

**Context:** This project extensively uses Pydantic's `BaseModel` for defining configuration schemas (e.g., `LLMConfig`, `GitConfig`, `GenerationConfig` in `prg_utils/config_schema.py`). Consistent application of `BaseModel` enhances code maintainability and reduces runtime errors by enforcing data structure.

**When to use:**
- Defining new configuration options for the tool.
- Creating data transfer objects (DTOs) for internal data representation.

**Check for:**
1. Classes representing configurations or data structures that do not inherit from `BaseModel`. This can lead to missing validation and type checking.
2. Inconsistent use of `Field` for providing default values and validation constraints within `BaseModel` classes.

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
# File: (Hypothetical - imagine a missing BaseModel inheritance)
class IncompleteConfig:  # Missing BaseModel!
    api_key: str
    enabled: bool = True
```

**Action items:**
1. Refactor any classes intended for configuration or data representation to inherit from `BaseModel` (e.g., `IncompleteConfig` in the hypothetical example above).
2. Review existing classes utilizing `BaseModel` to ensure consistent use of `Field` for default values and validation (see `prg_utils/config_schema.py`).

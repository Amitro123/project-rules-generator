### pydantic-config-models
Leverage Pydantic's BaseModel for structured configuration management.

**Context:** This project uses Pydantic's `BaseModel` extensively in `prg_utils/config_schema.py` to define the structure and validation rules for various configuration settings, including LLM, Git, Generation, Packs, and Skill Sources. Consistent use of Pydantic ensures type safety, validation, and easier management of configurations.

**When to use:**
- Defining new configuration options for the application.
- Modifying existing configuration structures.

**Check for:**
1. Missing type annotations or incorrect types in configuration classes, leading to runtime errors or unexpected behavior. For example, using `str` instead of `bool` for a boolean flag.
2. Lack of validation constraints (e.g., `Field(ge=1, le=20)`) on numerical or string fields, which could lead to invalid configurations.

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
# File: (hypothetical) prg_utils/bad_config.py
class BadConfig(BaseModel):
    enabled: str  # Should be bool
    max_value: int # Missing validation constraints
```

**Action items:**
1. Review all classes inheriting from `BaseModel` in `prg_utils/config_schema.py` and ensure correct type annotations and validation constraints are in place.
2. Add unit tests in `tests/test_config_schema.py` to validate that configuration classes enforce the defined constraints and handle invalid input correctly. Specifically, test that `ValidationError` is raised when invalid values are assigned to configuration fields.

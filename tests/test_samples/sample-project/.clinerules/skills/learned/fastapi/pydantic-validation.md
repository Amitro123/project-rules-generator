### pydantic-validation
Best practices and patterns for pydantic validation in this project.

**Context:** This project uses Pydantic models for data validation, which is critical for ensuring data integrity and preventing invalid data from being processed.

**Triggers:** ["adding new model", "modifying existing model", "adding validation logic"]

**relevant_files:** ["**/schemas/**", "**/models/**", "**/validators/**"]

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- Adding new models with complex validation rules
- Modifying existing models to add or remove fields
- Updating validation logic for existing models

**Check for:**
1. Missing `title` field in Pydantic models
```python
# File: src/schemas/user.py:5
class UserSchema(BaseModel):
    username: str
    email: EmailStr
```

**Good pattern (from this project):**
```python
# File: src/schemas/response.py:12
class ErrorResponse(BaseModel):
    """Default error response."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
```

**Tools:**
```bash
check: ruff check --select S --select V **/schemas/*/** **/models/*/**
test:  pytest tests/test_schemas.py -v
lint:  mypy src/schemas/*/** --strict
```

**Action items:**
1. `ruff check --select S --select V src/schemas/user.py` — find missing `title` field
2. `pytest tests/test_schemas.py -v` — verify schema coverage
3. `grep -rn "BaseModel" **/schemas/*/** | grep -v "title"` — find models missing `title` field
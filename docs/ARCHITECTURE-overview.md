# Architecture: Project Rules Generator (PRG)

## Problem Statement
PRG automates the creation of context-aware AI agent rules by analyzing local project patterns, structure, and documentation, replacing static templates with dynamic, learned expertise.

## Architecture Decisions

- **Implementation Approach**: Modular design with dependency injection. Enables testable components and flexible dependency mocking, albeit with more upfront design effort.
- **Error Handling**: Graceful degradation with fallbacks. Ensures system availability and better UX during partial outages, requiring robust logging.

## API Contracts

- ### `execute_complete(params: dict) -> Result`

**Purpose**: Execute the full project analysis and rule generation sequence.

**Parameters**:
- `params`: Operation parameters

**Returns**: Operation result

**Raises**:
- `ValidationError`: If params are invalid
- `OperationError`: If execution fails


## Data Models

- ```python
class CompleteConfig(BaseModel):
    """Configuration for PRG project analysis and generation."""
    enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)
```

## Success Criteria

- **Functionality**: Rule generation and skill analysis works as specified.
- **Quality**: Test coverage > 80%
- **Performance**: Operation completes in < 1 second
- **Maintainability**: Code follows project style guide

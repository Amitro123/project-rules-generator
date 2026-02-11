### error-handling
Skill: Error Handling
Purpose: Handle exceptions following project patterns.

**Triggers:**
- Exception handling needed
- `sys.exit()` detected
- Bare `except` blocks

**DO:**
- Use `ProjectRulesGeneratorError` for app errors
- `logging.error()` instead of `print()`
- Specific except: `except ValueError as e:`
- Let Click handle CLI exit codes

**DON'T:**
- Bare `except: Exception`
- `sys.exit()` in library code
- `print()` for errors

**Example:**
```python
try:
    config = GenerationConfig(**data)
except ValidationError as e:
    logging.error(f"Invalid config: {e}")
    raise ProjectRulesGeneratorError("Config validation failed")
```

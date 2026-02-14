### error-handling
Best practices and patterns for error handling in this project.

**Context:** Error handling is critical for a reliable CLI application like codereview-agent. Proper error handling ensures that the application remains stable even when unexpected errors occur.

**Triggers:** ["adding error-prone code", "modifying exception handling", "error reporting"]

**relevant_files:** []

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- Implementing error-prone features
- Modifying exception handling logic
- Improving error reporting

**Check for:**
1. Missing try-except blocks in async functions
2. Unhandled exceptions in error-prone code (e.g., file I/O, network requests)

**Good pattern (from this project):**
```python
# File: src/api/main.py:25
try:
    # Code that might raise an exception
    await client.connect()
except Exception as e:
    # Handle the exception properly
    logger.error(f"Database connection failed: {e}")
    return {"error": "Failed to connect to database"}
```

**Tools:**
```bash
check:  flake8 src/api/ --select E722
test:  pytest tests/test_errors.py -v
lint:  mypy src/api/main.py --strict
```

**Action items:**
1. `flake8 src/api/ --select E722` — find missing try-except blocks
2. `pytest tests/test_errors.py -v` — verify error handling coverage
3. `grep -rn "except" src/api/ | grep -v "logger"` — find unhandled exceptions
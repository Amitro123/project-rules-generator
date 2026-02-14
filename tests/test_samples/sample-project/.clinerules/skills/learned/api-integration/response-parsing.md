### response-parsing
Best practices and patterns for response parsing in this project.

**Context:** Efficient response parsing is crucial for handling API responses, especially when dealing with large datasets or complex structures.

**Triggers:** ["handling large API responses", "parsing complex JSON data"]

**relevant_files:** []

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- Handling large API responses
- Parsing complex JSON data

**Check for:**
1. Missing error handling for `JSONDecodeError` exceptions
2. Inefficient use of `json.loads()` for parsing large responses

**Good pattern (from this project):**
```python
# File: src/api/utils/response.py:20
import json

def parse_response(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse response: {e}")
        return {}
```

**Tools:**
```bash
check:  flake8 src/api/utils/response.py --select F
test:   pytest tests/test_response.py -v
lint:   mypy src/api/utils/response.py --strict
```

**Action items:**
1. `flake8 src/api/utils/response.py --select F` — find missing `try-except` blocks
2. `pytest tests/test_response.py -v` — verify response parsing coverage
3. `grep -rn "json.loads\(" src/api/utils/response.py | grep -v "try"` — find inefficient `json.loads()` usage
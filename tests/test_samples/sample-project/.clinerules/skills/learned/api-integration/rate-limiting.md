### fastapi-rate-limit-patterns
Best practices and patterns for rate limiting in FastAPI using headers and rate limiting middleware.

**Context:** This project uses FastAPI with FastAPI's built-in rate limiting feature to prevent abuse of endpoints.

**Triggers:** ["adding rate limit logic", "modifying endpoint permissions", "performance optimization"]

**relevant_files:** []

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**", "**/.git/**"]

**When to use:**
- Adding rate limit logic to critical endpoints
- Modifying endpoint permissions to prevent abuse

**Check for:**
1. Missing rate limiting middleware for sensitive endpoints
2. Incorrectly configured rate limiting headers

**Good pattern (from this project):**
```python
# File: src/main.py:25
from fastapi import FastAPI
from fastapi_limiter_keycloak import FastAPILimiter

app = FastAPI(title="Codereview Agent")
limiter = FastAPILimiter(app)

@app.get("/api/v1/users")
def get_users():
    return [{"id": 1, "name": "John"}]
```

**Tools:**
```bash
check: ruff check --select S src/main.py
test:  pytest tests/test_rate_limit.py -v
lint:  mypy src/main.py --strict
```

**Action items:**
1. `ruff check --select S src/main.py` — find missing rate limiting middleware
2. `pytest tests/test_rate_limit.py -v` — verify rate limit coverage
3. `grep -rn "limit\." src/main.py | grep -v "FastAPILimiter"` — find incorrectly configured rate limiting headers
4. `curl -X GET http://localhost:8000/api/v1/users -H "X-RateLimit-Limit: 1"` — test rate limiting headers
5. `curl -X GET http://localhost:8000/api/v1/users -H "X-RateLimit-Remaining: 0"` — test rate limiting headers
6. `curl -X GET http://localhost:8000/api/v1/users -H "X-RateLimit-Reset: 0"` — test rate limiting headers

Note: These action items are based on the example code provided and may not reflect the actual codebase of the project.
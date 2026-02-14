### retry-error-handling
Best practices and patterns for retry error handling in this project.

**Context:** This project uses asynchronous requests and may encounter network errors or timeout issues. Implementing retry error handling is crucial to ensure reliability and robustness.

**Triggers:** ["async request failed", "network error", "timeout exception"]

**relevant_files:** []

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- When making asynchronous requests to external APIs
- When encountering network errors or timeout issues

**Check for:**
1. Missing retry logic for async requests
   ```python
# File: src/main.py:25
async def make_async_request():
    try:
        # async request code here
    except aiohttp.ClientError:
        # handle exception
        pass
```
   **Fix:** Add retry logic using `aiohttp.ClientSession` with `limit` and `backoff_factor` parameters.
   ```python
# File: src/main.py:25
async def make_async_request():
    session = aiohttp.ClientSession(limit=10, backoff_factor=0.1)
    try:
        async with session.get(url) as response:
            # async request code here
    except aiohttp.ClientError:
        # handle exception
        pass
    finally:
        await session.close()
```

**Good pattern (from this project):**
```python
# File: src/main.py:25
import asyncio
import aiohttp

async def make_async_request():
    session = aiohttp.ClientSession(limit=10, backoff_factor=0.1)
    try:
        async with session.get(url) as response:
            # async request code here
    except aiohttp.ClientError as e:
        # handle exception
        print(f"Error: {e}")
    finally:
        await session.close()
    return response.status
```

**Tools:**
```bash
check: ruff check --select S src/main.py
test:  pytest tests/test_retry.py -v
lint:  mypy src/main.py --strict
```

**Action items:**
1. `ruff check --select S src/main.py` — find missing retry logic
2. `pytest tests/test_retry.py -v` — verify retry coverage
3. `grep -rn "async with" src/main.py | grep -v "session"` — find async requests missing retry logic
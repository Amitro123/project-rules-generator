### middleware-patterns
Best practices and patterns for middleware patterns in this project.

**Context:** This project's use of FastAPI and uvicorn requires proper middleware configuration to ensure security and performance.

**Triggers:** ["adding custom middleware", "configuring CORS", "logging setup"]

**relevant_files:** []

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- Adding custom middleware functions
- Configuring CORS headers for API endpoints
- Setting up logging for the application

**Check for:**
1. Missing `@app.middleware` decorator for custom middleware
2. Inconsistent logging configuration across the application

**Good pattern (from this project):**
```python
# File: src/main.py:20
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware function
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - request.start_time)
    return response
```

**Tools:**
```bash
check: ruff check --select S src/main.py
test:  pytest tests/test_middleware.py -v
lint:  mypy src/main.py --strict
```

**Action items:**
1. `ruff check --select S src/main.py` — find missing middleware decorators
2. `pytest tests/test_middleware.py -v` — verify middleware coverage
3. `grep -rn "app.add_middleware" src/main.py | grep -v "CORSMiddleware"` — find inconsistent CORS configurations
### api-client-patterns
Best practices and patterns for API client usage in this project.

**Context:** Proper API client usage is crucial for maintaining a well-structured and efficient API client implementation in this project, which relies heavily on FastAPI and WebSockets for communication.

**Triggers:** ["adding new API endpoint", "modifying client-side logic", "integrating with external services"]

**relevant_files:** ["**/routes/**", "**/endpoints/**", "**/api/**", "**/views/**", "**/cli.py", "**/main.py", "**/commands/**"]

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- Adding new API endpoints for external services
- Integrating with new external services

**Check for:**
1. **Missing API endpoint documentation**: Ensure that all API endpoints have clear and accurate documentation.
```python
# File: src/api/endpoints/users.py:23
from fastapi import APIRouter
from src.api.schemas.users import UserListResponse

router = APIRouter()
@router.get("/users")
async def get_users():
    # This endpoint lacks documentation
    return {"users": [...]}

```
2. **Unclear API endpoint naming conventions**: Verify that all API endpoint names follow the agreed-upon naming conventions.

**Good pattern (from this project):**
```python
# File: src/api/endpoints/users.py:10
from fastapi import APIRouter
from src.api.schemas.users import UserResponse

router = APIRouter()
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```
**Tools:**
```bash
check: ruff check --select S src/api/endpoints/*
test:  pytest tests/test_api.py -v
lint:  mypy src/api/endpoints/ --strict
```
**Action items:**
1. `ruff check --select S src/api/endpoints/` — find missing endpoint documentation
2. `pytest tests/test_api.py -v` — verify API endpoint coverage
3. `grep -rn "router\." src/api/endpoints/ | grep -v "Depends"` — find endpoints with unclear naming conventions
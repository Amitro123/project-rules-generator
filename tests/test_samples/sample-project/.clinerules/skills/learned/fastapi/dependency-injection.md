### dependency-injection-patterns
Best practices and patterns for dependency injection in this project.

**Context:** Proper dependency injection is crucial for maintainable and scalable codebases. This project relies heavily on FastAPI and its dependency injection features.

**Triggers:**["adding new service", "modifying existing endpoint", "dependency injection mismatch"]

**relevant_files:** []

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- Adding new services or endpoints
- Modifying existing endpoints with new dependencies
- Resolving dependency injection mismatches

**Check for:**
1. Missing dependency injection for FastAPI endpoints
    - **Code example:** 
    ```python
# File: src/api/routes/users.py:20
@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User):
    return current_user
```

    - **Fix:** Add `Depends(get_current_active_user)` to inject the `current_user` dependency.
    ```python
# File: src/api/routes/users.py:20
@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    return current_user
```

2. Hardcoded dependencies instead of using FastAPI's dependency injection
    - **Code example:** 
    ```python
# File: src/api/services/users.py:10
def get_user_data():
    return User.query.all()
```

    - **Fix:** Inject the `User` model through FastAPI's dependency injection.
    ```python
# File: src/api/services/users.py:10
from fastapi import Depends
from src.api.models.user import User

def get_user_data(User: User = Depends(get_db)):
    return User.query.all()
```

**Good pattern (from this project):**
```python
# File: src/api/services/users.py:5
from fastapi import Depends
from src.api.models.user import User

def get_user(User: User = Depends(get_db)):
    return User.query.all()
```

**Tools:**
```bash
check: ruff check --select S src/api/services/*.py
test:  pytest tests/test_dependency_injection.py -v
lint:  mypy src/api/services/*.py --strict
```

**Action items:**
1. `ruff check --select S src/api/services/*.py` — find missing dependency injection
2. `pytest tests/test_dependency_injection.py -v` — verify dependency injection coverage
3. `grep -rn "Depends" src/api/services/*.py | grep -v "get_db"` — find hardcoded dependencies
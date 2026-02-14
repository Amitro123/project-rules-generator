### async-patterns
Best practices and patterns for async patterns in this project.

**Context:** This project uses asynchronous code for tasks and workers, which requires careful handling to avoid performance issues and deadlocks.

**Triggers:** ["adding async endpoint", "modifying worker logic", "async task timing out"]

**relevant_files:** ["**/tasks/**", "**/workers/**", "**/celery*.py"]

**exclude_files:** ["**/*.pyc", "**/__pycache__/**", "**/.venv/**", "**/node_modules/**"]

**When to use:**
- Adding new async endpoints
- Modifying worker timing or logic
- Creating new async tasks

**Check for:**
1. Missing `await` statements in async functions
2. Async tasks not properly cancelled when completed

**Good pattern (from this project):**
```python
# File: src/workers/tasks.py:23
async def async_task(
    current_user: User = Depends(get_current_active_user)
) -> None:
    try:
        # async operations...
        await db.query(User).filter(User.id == current_user.id).delete()
    except Exception as e:
        logging.error(f"Error in async task: {e}")
    finally:
        await db.close()  # close db connection
```

**Tools:**
```bash
check:  black --check src/workers/
test:   pytest tests/test_tasks.py -v
lint:   flake8 src/workers/
```

**Action items:**
1. `black --check src/workers/` — find missing `await` statements
2. `pytest tests/test_tasks.py -v` — verify task coverage
3. `grep -rn "async def" src/workers/* | grep -v "await"` — find async functions missing `await` statements
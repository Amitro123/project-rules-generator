---
name: pytest-best-practices
description: |
  Provides best practices and patterns for writing effective and maintainable tests using pytest in this Python project.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [pytest, testing, python, best-practices, quality, has_tests]
---

# Skill: Pytest Best Practices

## Purpose

This skill helps ensure that the project's Python tests, leveraging the `pytest` framework, adhere to best practices for readability, maintainability, and efficiency. By following these guidelines, the project's `has_tests` pattern will result in a robust and reliable test suite, improving code quality and reducing future debugging efforts.

## Auto-Trigger

Activate when the user mentions:
- **"pytest best practices"**
- **"improve test quality"**
- **"how to write good tests"**

Do NOT activate for: "run tests", "fix test", "debug test"

## CRITICAL

- Ensure `pytest` is installed and the environment is consistent before attempting to run tests or apply fixes.
- Do not invent specific test file contents or `conftest.py` fixtures that are not present in the provided context. Focus on general patterns.

## Process

### 1. Verify Pytest Installation

Before applying any best practices, confirm that `pytest` is installed in your development environment. This ensures that test commands will execute correctly.

```bash
pip show pytest
```
If `pytest` is not found, install it:
```bash
pip install pytest
```

### 2. Run Existing Tests

Execute the current test suite to understand its existing structure and identify any immediate issues or areas for improvement. This helps establish a baseline.

```bash
pytest
```

### 3. Implement General Best Practices

Focus on structuring tests for clarity and efficiency. Given the project has a `has_tests` pattern, good organization is key.
- **Clear Naming Conventions:** Name test files `test_*.py` or `*_test.py` and test functions `test_*` to ensure `pytest` automatically discovers them.
- **Fixture Usage:** Utilize `conftest.py` for shared fixtures to promote reusability and avoid code duplication across tests.
- **Parameterization:** Use `@pytest.mark.parametrize` to test multiple input scenarios with a single test function, reducing boilerplate.
- **Assertions:** Use standard `assert` statements for clarity.

## Validate

After implementing changes or reviewing test structure, run `pytest` again to ensure all tests pass and the new practices are correctly applied.

```bash
pytest
```

## Output

- A more organized and maintainable test suite.
- Improved clarity and readability of individual tests.
- Enhanced efficiency in testing through fixtures and parameterization.

## Anti-Patterns

❌ **Don't** write monolithic test functions that test multiple unrelated aspects.
✅ **Do** write small, focused test functions that test a single piece of functionality.

❌ **Don't** duplicate setup/teardown logic across multiple test files.
✅ **Do** use `conftest.py` to define reusable fixtures for common setup and teardown tasks.

## Examples

```python
# General pattern for a test file (e.g., tests/test_my_module.py)
# Note: This is a general example and does not reference specific project files.

import pytest

# Example function to be tested (assume it exists in main.py or another module)
def add(a, b):
    return a + b

def test_add_positive_numbers():
    assert add(1, 2) == 3

def test_add_negative_numbers():
    assert add(-1, -2) == -3

@pytest.mark.parametrize("a, b, expected", [
    (1, 1, 2),
    (0, 0, 0),
    (-5, 5, 0),
    (100, 200, 300),
])
def test_add_various_inputs(a, b, expected):
    assert add(a, b) == expected

# General pattern for a conftest.py file in the root of the tests directory
# This file defines fixtures that can be used across multiple test files.
# Note: This is a general example and does not reference specific project files.

# import pytest

# @pytest.fixture
# def sample_data():
#     """A simple fixture providing data for tests."""
#     return {"key": "value", "count": 10}

# @pytest.fixture(scope="session")
# def database_connection():
#     """A session-scoped fixture for a database connection."""
#     print("\nSetting up database connection...")
#     # Simulate connection
#     conn = "DatabaseConnectionObject"
#     yield conn
#     print("\nClosing database connection...")
#     # Simulate disconnection
```
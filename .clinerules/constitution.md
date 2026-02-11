# Code Quality Principles

## Linting & Formatting

To ensure consistent code quality, follow these guidelines:

### Enforce Linting and Formatting

- Run `ruff check .` and `mypy .` before committing code changes.
- Use a code editor or IDE that supports auto-formatting and linting, such as PyCharm or VSCode with the `ruff` and `mypy` extensions.
- Configure your editor or IDE to run these checks on save to catch errors early.

### Enforce Type Hints

- Use type hints for all public APIs, including function parameters and return types.
- Use the `mypy` configuration to enforce type hints.

### Data Validation

- Use Pydantic models for data validation and serialization.
- Validate inputs with Pydantic models instead of raw dictionaries.

## Testing Standards

### Framework

- Use `pytest` as the testing framework.
- Run `pytest` before merging any changes to ensure test coverage.

### Test Structure

- Store test data in `tests/fixtures/`.
- Use shared fixtures from `conftest.py` to avoid duplicating test setup.
- Use descriptive test names and ensure each test has a clear purpose.

### Test Types

- Use unit tests to verify individual components.
- Use integration tests to verify how components interact.

### Test Coverage

- Ensure each new feature or bug fix includes corresponding tests.
- Use tools like `pytest-cov` to measure test coverage.

## Architecture Decisions

### Project Type

- This project is a Python CLI application.

### Entry Points

- The main entry point is `main.py`.

### Structural Patterns

- Use the Python CLI pattern for command-line interfaces.
- Use the Pytest pattern for testing.

### CLI Commands

- Use Click decorators for CLI commands.
- Keep command functions thin and focused on a single task.

## Development Guidelines

### Detected Tools

- **test**: `pytest`
- **check**: `ruff check .`
- **lint**: `mypy .`

### Key Paths

- `main.py`

### Version Control

- Never commit secrets, API keys, or `.env` files.
- Write descriptive commit messages following conventional commits.
- Keep module imports at the top of each file; use absolute imports within the project.

## Example Use Cases

- To enforce type hints, use the `mypy` configuration to check for type hints in your code.
- To validate inputs, use Pydantic models to ensure data is in the correct format.

## Code Examples

- **Enforce Type Hints**
```python
from typing import List

def greet(name: str) -> str:
    return f"Hello, {name}!"
```
- **Validate Inputs with Pydantic**
```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

user = User(name="John Doe", email="john@example.com")
print(user.json())
```
- **Use Click Decorators for CLI Commands**
```python
import click

@click.group()
def cli():
    pass

@cli.command()
@click.argument("name")
def greet(name):
    click.echo(f"Hello, {name}!")
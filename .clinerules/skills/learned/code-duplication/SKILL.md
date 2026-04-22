---
name: code-duplication-best-practices
description: |
  Identifies and refactors duplicate Python code within this project, leveraging its testing infrastructure and GitHub Actions for validation.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [code-quality, refactoring, python, gemini, github-actions, maintainability, testing]
---

# Skill: Code Duplication Best Practices

## Purpose

This skill helps identify and eliminate redundant code blocks, which can lead to maintainability issues, increased bug surface area, and slower development. For this project, with its Python codebase, existing tests (`has_tests`), and CI/CD via GitHub Actions, reducing duplication ensures a more robust, easier-to-understand, and efficient application, especially when integrating with AI models like Gemini.

## Auto-Trigger

Activate when the user mentions:
- **"code duplication"**
- **"duplicate code"**
- **"refactor repetitive code"**

Do NOT activate for: "copy file", "clone repository", "copy paste text"

## CRITICAL

- Always ensure all existing tests pass after any refactoring. This project `has_tests`, which are your primary safety net.
- Verify that changes do not introduce regressions or alter the project's behavior, especially in core logic or Gemini model interactions.
- Before attempting to reproduce or fix CI/CD issues related to duplication, verify environment parity (e.g., Python version, installed packages) between your local setup and the GitHub Actions runner.

## Process

### 1. Detect Potential Duplication

Use `grep` to scan for identical or highly similar code patterns across your Python files. Focus on common logic, utility functions, or data processing steps that might be repeated.

```bash
grep -r "def common_function_name(" .
# OR, for a specific pattern you suspect is duplicated:
grep -r -E "pattern_of_suspected_duplicate_code" .
```

### 2. Analyze and Refactor Duplicated Code

Review the identified patterns. If a block of code is repeated in multiple places, consider extracting it into a reusable function, class method, or a dedicated module within your `main_directories` structure.

**Example Refactoring Strategy (Generic Python):**

If you find a pattern like this:

```python
# In file_a.py
def process_data_a(data):
    # ... some initial processing ...
    result = data * 2 + 10
    # ... some final processing ...
    return result

# In file_b.py
def process_data_b(data):
    # ... some different initial processing ...
    result = data * 2 + 10 # This line is duplicated
    # ... some different final processing ...
    return result
```

You would refactor by extracting the common part:

```python
# In a new or existing utility module (e.g., utils.py)
def _common_calculation(value):
    return value * 2 + 10

# In file_a.py
def process_data_a(data):
    # ... some initial processing ...
    result = _common_calculation(data)
    # ... some final processing ...
    return result

# In file_b.py
def process_data_b(data):
    # ... some different initial processing ...
    result = _common_calculation(data)
    # ... some different final processing ...
    return result
```

### 3. Validate Changes

After refactoring, it's crucial to ensure that no regressions have been introduced.

```bash
# Run all tests in the project
python -m unittest discover
# OR if you have a specific test runner configured (e.g., pytest if it were in dependencies)
# pytest
```

Additionally, push your changes to trigger GitHub Actions to verify that your refactoring passes all CI checks.

## Output

- Reduced lines of code in the project.
- Improved code readability and maintainability.
- Passing local tests and successful GitHub Actions CI builds.
- Potentially new or modified Python files (e.g., `utils.py` for common functions) and updated existing files (e.g., `main.py` if it uses the common logic).

## Anti-Patterns

❌ **Don't** copy-paste code snippets without considering extracting them into reusable functions or modules.
✅ **Do** identify recurring logic and encapsulate it into a single, well-named function or class method, then call that function from all necessary locations.

## Examples

```python
# Generic example illustrating extraction of common logic,
# as the provided main.py is empty.

# Before (potential duplication in different functions/files):
def apply_standard_normalization(value):
    """Applies a standard normalization formula."""
    normalized = (value - 0.5) * 2.0
    return max(0.0, min(1.0, normalized)) # Clamping between 0 and 1

def process_sensor_data(raw_data):
    # ... other processing ...
    normalized_data = [apply_standard_normalization(val) for val in raw_data]
    # ... further processing ...
    return normalized_data

def prepare_for_gemini_input(feature_vector):
    # ... other preparation ...
    processed_vector = [apply_standard_normalization(f) for f in feature_vector]
    # ... further preparation ...
    return processed_vector

# After (extracting common normalization logic to a dedicated utility function):

# Assume this is in a shared utility file or module (e.g., project_utils.py)
def _clamp_and_normalize(value, min_val=0.0, max_val=1.0):
    """Applies a standard normalization formula and clamps the result."""
    normalized = (value - 0.5) * 2.0
    return max(min_val, min(max_val, normalized))

# Now, in files like main.py or other processing modules:
# from .project_utils import _clamp_and_normalize # (if in a package)

def process_sensor_data(raw_data):
    # ... other processing ...
    normalized_data = [_clamp_and_normalize(val) for val in raw_data]
    # ... further processing ...
    return normalized_data

def prepare_for_gemini_input(feature_vector):
    # ... other preparation ...
    processed_vector = [_clamp_and_normalize(f) for f in feature_vector]
    # ... further preparation ...
    return processed_vector
```
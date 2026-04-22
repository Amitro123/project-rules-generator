---
name: python-gemini-architecture-improvements
description: |
  Provides best practices for improving the architecture of Python projects leveraging Gemini, focusing on modularity, testability, and maintainability, especially with GitHub Actions.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [architecture, python, gemini, github-actions, refactoring, best-practices]
---

# Skill: Python/Gemini Architecture Improvements

## Purpose

This skill guides you through applying architectural best practices to your Python project, particularly when integrating with Gemini and using GitHub Actions for CI/CD. Given the project's `has_tests` and `main_directories` patterns, it emphasizes creating modular, scalable, and easily testable code, ensuring changes are robust and maintainable.

## Auto-Trigger

Activate when the user mentions:
- **"improve architecture"**
- **"refactor project structure"**
- **"best practices for python design"**

Do NOT activate for: linting, formatting, dependency updates, simple bug fixes

## CRITICAL

- All architectural changes must be implemented incrementally and verified with existing tests.
- Before making significant changes, ensure a clear understanding of the project's current functionality.
- Verify environment parity (e.g., Python version, installed packages) between your local setup and GitHub Actions when dealing with CI/CD changes.

## Process

### 1. Define Goals and Scope

Clearly articulate what specific architectural problem you are trying to solve (e.g., reduce coupling, improve testability, prepare for new features). Consider how a more robust architecture will benefit the integration with Gemini or the existing GitHub Actions workflows.

### 2. Propose Modular Design Changes

Based on your goals, propose specific structural changes. For a Python project, this often involves breaking down monolithic files or functions into smaller, more focused modules or packages. Think about clear separation of concerns (e.g., data handling, business logic, Gemini API interaction, utility functions). Since `main_directories` is detected, consider how new modules fit into the existing directory structure.

### 3. Implement Incrementally and Test

Make small, isolated changes. For each change, run the existing test suite to ensure no regressions are introduced. Leverage the `has_tests` pattern by adding new tests for any new functionality or modifying existing tests to reflect refactored code.

```bash
# Create a new branch for your architectural changes
git checkout -b feature/architecture-refactor

# After making code changes, run tests
python -m pytest

# Stage and commit your changes
git add .
git commit -m "feat: Implement modular architecture for X component"
```

### 4. Review and Update CI/CD (GitHub Actions)

If your architectural changes impact how the project is built, tested, or deployed (e.g., changes to main entry points, new dependencies), ensure your GitHub Actions workflows are updated accordingly. This might involve modifying workflow files to reflect new paths or commands.

```bash
# Push your branch to trigger GitHub Actions for verification
git push origin feature/architecture-refactor
```

## Validate

After implementing changes and pushing to your feature branch, verify that all tests pass both locally and in your GitHub Actions CI/CD pipeline.

```bash
# Run all tests locally
python -m pytest

# Check GitHub Actions workflow runs for your branch
# (This is a conceptual step; actual check is via browser/GitHub CLI)
```

## Output

- Improved code readability and maintainability.
- A more modular and scalable project structure.
- Potentially updated `requirements.txt` or `pyproject.toml` if dependencies change.
- Verified GitHub Actions workflows that correctly build and test the refactored project.

## Anti-Patterns

❌ **Don't** create large, single-responsibility-breaking modules or functions (e.g., a `main.py` that handles all data parsing, Gemini interaction, and business logic).
✅ **Do** decompose functionality into smaller, cohesive modules, each with a clear responsibility.

❌ **Don't** introduce architectural changes without corresponding automated tests or without verifying against the existing test suite.
✅ **Do** ensure all new or modified logic is covered by automated tests, leveraging the `has_tests` pattern.

## Examples

```python
# Generic example demonstrating modularity, without specific file paths.

# BEFORE (conceptual 'main.py' handling too much)
# def process_data_and_call_gemini(raw_input):
#     processed_data = preprocess(raw_input)
#     gemini_response = gemini_api_call(processed_data)
#     return parse_gemini_response(gemini_response)

# AFTER (more modular approach)

# In a data_processing_module.py
def preprocess_data(raw_input: str) -> str:
    """Cleans and formats raw input data."""
    # ... implementation ...
    return raw_input.strip()

# In a gemini_service_module.py
def call_gemini_api(data: str) -> dict:
    """Makes an API call to Gemini with processed data."""
    # ... implementation using Gemini SDK ...
    return {"response": f"Gemini processed: {data}"}

def parse_gemini_response(api_response: dict) -> str:
    """Extracts relevant information from Gemini's response."""
    # ... implementation ...
    return api_response.get("response", "No response")

# In main.py (or a higher-level orchestrator)
def orchestrate_gemini_workflow(input_text: str) -> str:
    """Orchestrates the data processing and Gemini interaction."""
    processed_data = preprocess_data(input_text)
    gemini_raw_response = call_gemini_api(processed_data)
    final_result = parse_gemini_response(gemini_raw_response)
    return final_result

# Usage
# result = orchestrate_gemini_workflow("  hello world  ")
# print(result) # Expected: Gemini processed: hello world
```
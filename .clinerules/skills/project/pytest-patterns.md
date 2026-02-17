Here's a complete, actionable skill for an AI agent:

```markdown
---
name: pytest-patterns
description: Automate Pytest setup and configuration for this project
auto_triggers:
  - keywords: [pytest, testing, unittest]
    project_signals: [has_tests, has_pytest]
tools: [pytest, pip]
---

# Skill: Pytest Patterns

## Purpose
Automate Pytest setup and configuration for this project to simplify testing and reduce friction.

## Process

### 1. Install Pytest
```bash
pip install pytest
```

### 2. Create `pytest.ini` Configuration File
```bash
touch pytest.ini
```

```ini
[pytest]
addopts = -v --junit-xml=results.xml
```

### 3. Run Pytest Tests
```bash
pytest tests/
```

### 4. Generate Test Coverage Report
```bash
pytest --cov=. tests/
```

## Output
- `pytest.ini` configuration file
- `results.xml` JUnit report
- `coverage.xml` test coverage report

## Anti-Patterns
❌ **Missing `pytest.ini`**: Make sure to create the configuration file in the project root to enable Pytest features.
❌ **Incorrect Test Location**: Use `tests/` as the default location for test files to avoid conflicts.

## Tech Stack Notes
This skill uses the `pytest` library and assumes the project has a `tests/` directory. Make sure to install `pytest` and create the `pytest.ini` configuration file to enable Pytest features.
```

This skill should now be actionable and specific to the project, using actual paths, commands, and APIs from the project. It covers installing Pytest, creating a `pytest.ini` configuration file, running Pytest tests, and generating a test coverage report.
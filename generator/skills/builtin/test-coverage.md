---
name: test-coverage
description: |-
  When the user wants to check test coverage.
  When the user wants to run tests and see coverage reports.
  When the user asks to verify that tests pass.
tools:
  - exec
---

## Description
Run tests and generate coverage.

## Tools
exec, pytest

## Triggers
- check coverage
- run tests

## Usage
```bash
pytest --cov=src --cov-report=term
```

---
name: pytest-debugger
description: |
  Developers struggling with debugging pytest tests can quickly pinpoint and resolve issues by setting breakpoints and inspecting variables directly within their test execution flow.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [testing, debugging, python, pytest]
---

# Skill: Pytest Debugger

## Purpose

Without interactive debugging, developers often resort to excessive print statements or guesswork to understand why their pytest tests are failing, leading to longer debugging cycles and frustration. This skill provides a structured approach to enable interactive debugging of pytest tests, accelerating the identification and resolution of test failures.

## Auto-Trigger

Activate when the user mentions:
- **"debug pytest"**
- **"breakpoint in test"**
- **"step through tests"**

Do NOT activate for: "debug application", "debug CI", "debug script"

## CRITICAL

- Ensure you have `pytest` installed in your environment.
- Verify that your test files are discoverable by `pytest` (typically in a `tests/` directory).

## Process

### 1. Set Breakpoints

[WHY this step matters — Without explicit breakpoints, the debugger has no specific line to pause execution, rendering it unable to inspect the test's state at a critical juncture.]

```bash
# Open your test file and add 'breakpoint()' or 'import pdb; pdb.set_trace()'
# at the line where you want execution to pause.
# Example:
# def test_example():
#     x = 1
#     breakpoint()  # Execution will pause here
#     assert x == 1
```

### 2. Run Pytest with Debugger

[WHY this step matters — Running pytest without specific flags will execute tests normally, bypassing any breakpoints you've set. This command ensures the debugger is activated.]

```bash
# Use pytest's --pdb flag to automatically invoke the debugger on test failures,
# or run with Python's -m pdb to manually control execution and breakpoints.
pytest --pdb
# or for more granular control with manually set breakpoints:
python -m pdb <your_test_file.py>
```

### 3. Validate

[WHY validation matters here specifically — Simply running the debugger doesn't guarantee it's attached or pausing as expected. This step confirms the debugger is active and ready for interaction.]

```bash
# After running pytest with --pdb or python -m pdb, you should see a debugger prompt (e.g., '(Pdb)')
# indicating that execution has paused. If you don't see this, re-check your setup and breakpoints.
echo "Debugger prompt should be visible in your terminal."
```

## Output

- An interactive debugging session within your terminal.
- Ability to step through test execution line by line.
- Inspection of variable values at any breakpoint.
- Modified test files with added `breakpoint()` calls (which should be removed after debugging).

## Anti-Patterns

❌ **Don't** leave `breakpoint()` or `pdb.set_trace()` calls in your code after debugging is complete, as they will halt normal test execution and CI/CD pipelines.
✅ **Do** remove all debugging statements from your code once you have resolved the issue.

## Examples

```python
# Example of setting a breakpoint in a test file
# tests/test_example.py

import pytest

def test_addition():
    a = 5
    b = 10
    result = a + b
    breakpoint()  # Execution pauses here
    assert result == 15

def test_subtraction():
    x = 20
    y = 5
    difference = x - y
    assert difference == 15
```
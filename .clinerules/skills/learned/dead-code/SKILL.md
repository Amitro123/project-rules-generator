---
name: identify-and-remove-dead-code
description: |
  Identifies and removes unused code in this Python project to improve maintainability and performance, leveraging existing tests.
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  tags: [python, dead-code, maintenance, refactoring, code-quality]
---

# Skill: Identify and Remove Dead Code

## Purpose

This skill helps maintain a clean and efficient Python codebase by identifying and removing code that is no longer used. For this project, which utilizes Python and has established tests, removing dead code reduces bundle size, improves readability, and minimizes potential security vulnerabilities, ensuring that the `main.py` and other core components remain focused and performant.

## Auto-Trigger

Activate when the user mentions:
- **"remove dead code"**
- **"clean up unused code"**
- **"refactor for dead code"**

Do NOT activate for: "remove code", "delete file", "refactor code"

## CRITICAL

- Always run the project's tests before and after removing any code to ensure no unintended functionality is broken.
- Verify the current working environment (Python version, installed packages) before attempting to reproduce or fix issues related to code execution.
- If unsure about code usage, comment it out temporarily and run tests and observe behavior over time before permanent deletion.

## Process

### 1. Identify Potentially Unused Files or Functions

Start by looking for files or functions within `main_directories` that might not be referenced elsewhere. This initial scan is a heuristic and requires manual confirmation.

```bash
# List all Python files in main directories (adjust path if needed)
find . -type f -name "*.py"

# Example: Search for a specific function/class name 'my_unused_function'
# and see if it's called anywhere else in the project.
# Replace 'MyUnusedClass' or 'my_unused_function' with actual names you suspect.
# This command searches for definitions and then for calls, looking for uncalled definitions.
grep -r "def MyUnusedFunction(" .
grep -r "class MyUnusedClass:" .
# Then, search for usages (excluding the definition line itself if possible, or manually filter)
grep -r "MyUnusedFunction(" .
grep -r "MyUnusedClass(" .
```

### 2. Leverage Test Coverage Insights (Conceptual)

This project `has_tests`, which is a strong indicator of code that is actively used. While specific coverage tools are not listed in dependencies, the principle of test coverage can guide identification. Code that is completely unexercised by tests is a strong candidate for dead code.

*   **Action**: Review existing tests and consider which parts of the codebase they cover. Code that is not touched by any test is more likely to be dead. This step relies on manual inspection of test suites and code paths.

### 3. Manual Review and Confirmation

Carefully review any code identified in the previous steps. Understand its purpose (or lack thereof) within the current project context. Consult with other developers if available.

### 4. Run Tests Before Removal

Before making any changes, execute the project's test suite to establish a baseline and ensure everything is currently working as expected. This is crucial given the `has_tests` pattern.

```bash
# Assuming a standard Python test runner setup for 'has_tests'
# This command will vary based on the actual test framework (e.g., pytest, unittest)
# Given no specific test runner is defined, a common approach for `has_tests` is:
python -m unittest discover
# Or if `pytest` is used (though not in dependencies, it's a common pattern)
# pytest
```

### 5. Remove the Dead Code

Once confirmed, remove the identified dead code. Be mindful of indentation and surrounding code.

```bash
# Example: Manually edit the file to remove the dead code.
# Use your preferred editor, e.g., 'nano main.py' or 'vim main.py'
```

### 6. Validate

After removing the code, run the project's tests again to ensure that the removal did not introduce any regressions or break existing functionality.

```bash
# Re-run the tests to validate the changes
python -m unittest discover
# Or if `pytest` is used
# pytest
```

## Output

- A cleaner, more maintainable Python codebase.
- Modified `.py` files with dead code removed.
- Confirmation that existing tests still pass after removal.

## Anti-Patterns

❌ **Don't** remove code without verifying its actual usage across the entire project, especially in dynamically typed languages like Python where direct `grep` might miss indirect calls.
✅ **Do** use `grep` as an initial heuristic, but always follow up with manual review and thorough testing.

❌ **Don't** delete code permanently without a version control system (like Git) in place.
✅ **Do** commit changes to version control, making it easy to revert if an error is discovered later.

## Examples

```python
# Generic Python example without specific file references:

# ❌ Bad Pattern: Dead function 'calculate_old_value' that is no longer called
# def calculate_old_value(a, b):
#     return a * b + 5

def calculate_new_value(x, y):
    """Calculates the new value based on x and y."""
    return x + y * 2

def process_data(data_list):
    results = []
    for item in data_list:
        results.append(calculate_new_value(item, 10))
    return results

# ✅ Good Pattern: Removed the unused 'calculate_old_value' function
# Only relevant, called functions remain.

def calculate_new_value(x, y):
    """Calculates the new value based on x and y."""
    return x + y * 2

def process_data(data_list):
    results = []
    for item in data_list:
        results.append(calculate_new_value(item, 10))
    return results
```
---
name: ci-lint-failures
description: |
  Developers struggling with CI lint failures can use this skill to diagnose and fix linting issues locally before pushing code, preventing repeated CI pipeline failures.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [ci, linting, github-actions, python, troubleshooting]
---

# Skill: CI Lint Failures

## Purpose

Every time you push code that triggers a CI lint failure, you waste time waiting for the pipeline to complete and then debugging an issue that could have been caught locally. The common mistake is to rely solely on CI for linting feedback. This skill guides you through quickly identifying the cause of CI lint failures and reproducing them in your local environment, allowing you to fix issues efficiently before they ever reach the CI server.

## Auto-Trigger

Activate when the user mentions:
- **"ci lint failure"**
- **"github actions lint error"**
- **"fix linting in ci"**
- **"pipeline lint error"**

Do NOT activate for: linting setup, linting configuration, adding a linter

## CRITICAL

- For CI/CD troubleshooting, always verify that your local environment's tool versions (e.g., Python, linter) match the CI environment before attempting to reproduce issues. Mismatched versions can lead to different linting results.
- Never invent specific linter commands or package names unless they are explicitly provided in the project's dependencies or CI configuration.

## Process

### 1. Review CI Logs

To understand why the CI pipeline failed, you need to examine the detailed logs from the GitHub Actions run. This step helps identify the specific linter being used and the exact error messages it produced.

```bash
# Replace <run_id> with the ID of your failed GitHub Actions run
# You can find the run ID on the GitHub Actions page for your repository.
# If you have the GitHub CLI installed:
gh run view --web <run_id>
# If not, navigate to your repository on GitHub, go to the 'Actions' tab,
# click on the failed workflow run, and review the logs there.
```

### 2. Reproduce ALL lint checks locally

This project's CI runs four checks in order. Run them all locally before pushing:

```bash
# 1. Ruff (fast linter — catches unused imports, undefined names, etc.)
python -m ruff check .

# 2. Black (formatter — CI uses --check mode; will fail if any file needs reformatting)
python -m black --check .

# 3. isort (import order)
python -m isort --profile black --check-only .

# 4. mypy (type checking)
python -m mypy . --ignore-missing-imports
```

### 3. Auto-fix what can be fixed automatically

Black and isort can reformat in-place. **Always run on `.` (the whole repo)** — targeting subdirectories misses `_bmad/`, `prg_utils/`, and other top-level packages:

```bash
python -m black .
python -m isort --profile black .
```

Ruff can fix many issues automatically too:
```bash
python -m ruff check . --fix
```

Mypy errors require manual fixes — see the `mypy-type-errors` skill.

### 4. Verify all checks pass

```bash
python -m ruff check . && python -m black --check . && python -m isort --profile black --check-only . && python -m mypy . --ignore-missing-imports
```

All four must exit 0 before pushing.

### 5. Common failure patterns in this project

| Failure | Cause | Fix |
|---------|-------|-----|
| `black: would reformat X` | Code not formatted | Run `black tests/ generator/ cli/` |
| `isort: Imports incorrectly sorted` | Import order wrong | Run `isort --profile black .` |
| `ruff: F841 local variable assigned but never used` | Dead assignment | Remove the variable |
| `ruff: E402 module level import not at top` | Late import | Add `# noqa: E402` or move the import |
| `mypy: str \| None not compatible with str` | Missing Optional | Use `Optional[str]` annotation |
| `mypy: union-attr` | Accessing attr on union type | Guard with `hasattr()` or `if x is not None` |

### 6. Commit and push

```bash
git add -u
git commit -m "chore: fix lint/format issues"
git push
```

## Output

- A clean Git working directory, free of linting errors.
- A passing GitHub Actions pipeline, indicating successful linting.
- Modified project source files with corrected code style and quality issues.

## Anti-Patterns

❌ **Don't** push code to a new branch or commit without first running the project's linter locally.
✅ **Do** always run the linter locally as part of your pre-commit routine to catch issues early and avoid unnecessary CI runs.

## Examples

```python
# Good practice example: Clear, readable Python code adhering to common style guidelines.
# Although specific linters might have different rules,
# consistency and clarity are universally valued.

def calculate_area(length: float, width: float) -> float:
    """
    Calculates the area of a rectangle.

    Args:
        length: The length of the rectangle.
        width: The width of the rectangle.

    Returns:
        The calculated area.
    """
    if length <= 0 or width <= 0:
        raise ValueError("Length and width must be positive.")
    area = length * width
    return area

# Common linting anti-pattern (e.g., by Black/Flake8 for line length, Pylint for unused variables):
# def long_function_name(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, arg10):
#     unused_variable = 10
#     print(f"This is a very long line that might exceed the maximum character limit: {arg1 + arg2 + arg3 + arg4 + arg5 + arg6 + arg7 + arg8 + arg9 + arg10}")
#     return unused_variable
```
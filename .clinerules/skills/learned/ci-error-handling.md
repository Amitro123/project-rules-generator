---
description: How to handle Continuous Integration (CI) pipeline errors and failures.
---

### ci-error-handling
Skill: CI Error Handling
Purpose: Handle exceptions and failures in CI/CD pipelines (e.g., GitHub Actions) following project patterns.

**Triggers:**
- User reports a CI failure
- A GitHub Actions run link is provided
- CI pipeline badge shows failure

**DO:**
1. **Analyze the error**: 
   - View CI logs locally or via the provided link (using `gh run view <run-id> --log` if available, or fetch the URL directly).
   - Identify which step failed (e.g., linting, formatting, type checking, tests).
2. **Reproduce locally**:
   - Run the exact commands from `.github/workflows/ci.yml` locally to reproduce the issue.
   - For formatting: run `black --check .` and `isort --profile black --check-only .`
   - For linting: run `ruff check .`
   - For typing: run `mypy .`
   - For testing: run `pytest`
3. **Fix automatically**:
   - Run auto-formatters to fix styling issues: `black .` and `isort --profile black .`
   - Run `ruff check --fix .` for linting issues.
4. **Fix manually**:
   - If tests or type hinting fail, understand the context, edit the code, and rerun the checks locally.
5. **Verify and Push**:
   - Ensure all local checks pass.
   - Commit the structural fixes and push the changes to resolve the CI pipeline error.

**DON'T:**
- Blindly push code without reproducing and verifying the CI checks locally.
- Skip over formatting/linting tools if the CI runs them.
- Ignore `.github/workflows/ci.yml` or the project's test files.

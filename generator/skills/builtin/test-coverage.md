---
name: test-coverage
description: |-
  When the user wants to check test coverage.
  When the user wants to run tests and see coverage reports.
  When the user asks to verify that tests pass.
tools:
  - exec
---

# Skill: Test Coverage

## Purpose
Without coverage measurement, it is easy to ship code that is untested in the paths that matter most — edge cases, error handling, and branching logic. This skill runs the test suite with coverage reporting and identifies gaps that need attention.

## Auto-Trigger
- User says: "check coverage", "run tests", "show coverage report"
- Before merging a feature branch
- After adding new modules without tests

## Process

### 1. Run Tests with Coverage
Always run coverage on the full suite, not just changed files — new code can expose gaps in existing tests.
```bash
pytest --cov=. --cov-report=term-missing --tb=short
```

### 2. Review the Report
Focus on lines and branches missed in core logic — 100% coverage on utilities matters less than 80% on business logic.
- Lines marked `!` are not executed by any test
- Look for uncovered error handling paths
- Check that new code introduced this session has coverage

### 3. Identify Gaps
Prioritize uncovered paths by risk: untested error handlers and conditional branches are highest priority.

### 4. Add Missing Tests
Write targeted tests for each uncovered gap — do not pad coverage with trivial assertions.
```bash
pytest --cov=. --cov-report=term-missing --tb=short  # re-run to confirm improvement
```

## Output
Coverage report showing:
- Overall percentage
- Per-file breakdown
- Specific missing lines highlighted

## Anti-Patterns
❌ Treating 100% line coverage as the goal — branch coverage matters more
❌ Writing tests that only exercise the happy path
❌ Suppressing coverage for untested critical code paths

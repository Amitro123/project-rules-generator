---
name: test-driven-development
description: |-
  When the user is implementing a new feature or fixing a bug.
  When the user wants to write tests first before writing code.
  When the user is refactoring and needs to verify behaviour is preserved.
tools:
  - read
  - exec
---

# Skill: Test-Driven Development

## Purpose
Without writing tests first, it is easy to write code that passes in the happy path but misses edge cases — and tests added after the fact often test the implementation rather than the requirement. This skill enforces the RED-GREEN-REFACTOR cycle so tests drive design rather than rubber-stamp it.

## Auto-Trigger
- New feature implementation
- Bug fix
- Refactoring

## Process

### 1. RED — Write Failing Test
Write the test for desired behavior before writing any implementation — verifying it fails confirms the test actually exercises the right thing.
```bash
pytest tests/test_feature.py -v  # must FAIL here
```
Commit: `git commit -m "RED: test for feature-name"`

### 2. GREEN — Make It Pass
Write the minimal code needed to pass the test — no more. Over-engineering at this stage hides design feedback.
```bash
pytest tests/test_feature.py -v  # must PASS here
pytest  # all other tests must still pass
```
Commit: `git commit -m "GREEN: implement feature-name"`

### 3. REFACTOR — Clean Up
Improve code quality without changing behavior; the passing tests act as a safety net.
```bash
pytest  # must still pass after refactor
```
Commit: `git commit -m "REFACTOR: clean up feature-name"`

## Output
- Passing test suite with new test covering the feature
- Committed code in three phases (RED, GREEN, REFACTOR)
- Test that will catch future regressions

## Anti-Patterns
❌ Writing code before writing the test
❌ Not verifying the test fails first (RED phase)
❌ Writing too much implementation code at once
❌ Skipping the REFACTOR phase

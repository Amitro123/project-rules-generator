---
name: systematic-debugging
description: |-
  When the user reports a bug, error, or something not working.
  When there is a failing test or CI/CD failure.
  When the user sees an exception in logs or unexpected behaviour.
tools:
  - read
  - exec
  - search
---

# Skill: Systematic Debugging

## Purpose
Without a structured process, developers often guess at root causes and fix symptoms instead of the underlying problem — wasting time and leaving the bug latent. This skill prevents that by enforcing a 5-phase reproduce-locate-analyze-fix-verify cycle.

## Auto-Trigger
- User reports: "bug", "error", "not working", "failing test"
- CI/CD failure
- Exception in logs

## Process

### 1. Reproduce
Never diagnose a bug you cannot consistently reproduce — it leads to fixing the wrong thing.
```bash
# Run the failing test to get a stable reproduction
pytest tests/test_foo.py::test_failing -v
```
- Get exact steps to reproduce
- Identify expected vs actual behavior
- Create a minimal failing test

### 2. Locate
Find *where* it breaks before analyzing why; narrowing the search space saves time.
- **Binary Search**: Comment out half the code
- **Trace Backwards**: From error message back to source
- **Instrumentation**: Log state before/after suspected lines

### 3. Analyze
Understand *why* it breaks — check assumptions, data types, and recent changes.

### 4. Fix
Correct the logic, add input validation guards, and add logging if the failure mode was hard to detect.

### 5. Verify
Confirm the fix is complete before declaring done.
```bash
pytest  # all tests must pass, not just the originally failing one
```
- Failing test now passes
- No regressions introduced
- Manual verification if needed

## Output
- Committed fix with root-cause explanation in commit message
- Minimal failing test that will catch regressions
- Green CI build

## Anti-Patterns
❌ Guessing without reproducing first
❌ Fixing symptoms without finding root cause
❌ Declaring "fixed" without running the full test suite
❌ Skipping the minimal reproduction step

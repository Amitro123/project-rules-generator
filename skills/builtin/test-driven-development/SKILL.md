# Skill: Test-Driven Development

## Purpose
Enforce RED-GREEN-REFACTOR cycle for all new code.

## Auto-Trigger
- New feature implementation
- Bug fix
- Refactoring

## RED-GREEN-REFACTOR Cycle

### 🔴 RED: Write Failing Test
1. Write test for desired behavior
2. Run test → verify it FAILS
3. Commit: `git commit -m "RED: test for [feature]"`

### 🟢 GREEN: Make It Pass
1. Write minimal code to pass test
2. Run test → verify it PASSES
3. All other tests still pass
4. Commit: `git commit -m "GREEN: implement [feature]"`

### 🔵 REFACTOR: Clean Up
1. Improve code quality (no behavior change)
2. Run all tests → verify they PASS
3. Commit: `git commit -m "REFACTOR: clean up [feature]"`

## Rules
✅ ALWAYS write test first
✅ Run test and see it fail before writing code
✅ Write minimal code to pass
✅ Commit after each phase
❌ NEVER write code before test
❌ NEVER skip the RED phase
❌ NEVER refactor without passing tests

## Anti-Patterns
❌ Writing code then adding tests
❌ Not verifying test fails first
❌ Writing too much code at once
❌ Skipping refactor phase

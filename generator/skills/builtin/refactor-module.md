---
name: refactor-module
description: |-
  When the user wants to refactor code following project rules.
  When the user wants to clean up code or improve structure.
  When the user wants to reorganize a module or file.
tools:
  - read
  - edit
  - exec
---

# Skill: Refactor Module

## Purpose
Without a structured refactor process, developers make behavioral changes alongside structural ones — making it impossible to tell whether a regression came from the refactor or from a logic change. This skill separates structure from behavior so refactors are safe and verifiable.

## Auto-Trigger
- User says: "refactor", "clean up code", "improve structure"
- Module has grown beyond a single responsibility
- Code review identifies structural issues

## Process

### 1. Establish a Baseline
Run the full test suite before touching anything — refactoring without a green baseline means you cannot detect regressions.
```bash
pytest --tb=short
```

### 2. Read and Understand the Module
Understand what the module does and why before changing it — refactoring code you don't understand introduces bugs.
```bash
# Check all callers before renaming or moving anything
grep -r "from module" . --include="*.py"
```

### 3. Apply One Change at a Time
Each step must keep tests green — mix structural and behavioral changes and you lose the ability to bisect failures.
- Extract functions/classes
- Rename for clarity
- Move to better location
- Remove dead code

### 4. Verify After Each Step
```bash
pytest --tb=short  # must stay green throughout
```

## Output
Refactored module with:
- All existing tests still passing
- Diff showing only structural changes (no logic changes)
- Updated imports in all callers

## Anti-Patterns
❌ Mixing behavioral fixes with structural refactoring in the same commit
❌ Refactoring without a passing test suite as a baseline
❌ Renaming without checking all callers
❌ Removing code that "looks" unused without verifying

---
name: writing-plans
description: |-
  When the user wants to create an implementation plan.
  When the user says "let's implement this" or "create a plan".
  When a design has been approved and is ready to be broken into tasks.
tools:
  - read
  - edit
---

# Skill: Writing Implementation Plans

## Purpose
Without a concrete task breakdown, implementation plans are vague and unexecutable — developers waste time figuring out what to do instead of doing it. This skill breaks approved designs into bite-sized, independently testable tasks (2-5 minutes each) so any agent or developer can execute them without ambiguity.

## Auto-Trigger
- After design approval (DESIGN.md exists)
- User says: "Let's implement this", "Create a plan"
- Before starting implementation

## Process

### 1. Read the Design
Understand scope and architecture decisions before breaking anything down — incorrect task boundaries cause rework.

### 2. Define Task Structure
Each task must have exactly: goal, files, changes, tests, and dependencies.
```
Task 1: Add user login endpoint
Dependencies: None
Files: src/auth/login.py, tests/test_login.py
Changes:
  - Add POST /login route with email+password validation
  - Return JWT token on success, 401 on failure
Tests: pytest tests/test_login.py -v (expect 2 passing tests)
Estimated time: 5 min
```

### 3. Check Task Size
Tasks that take > 10 minutes cannot be assigned to a single subagent cleanly — split them.
✅ 2-5 minutes per task
✅ Single responsibility
✅ Independently testable

### 4. Write PLAN.md
```bash
# Verify the plan covers all design requirements
grep -c "^Task" PLAN.md  # should match number of design subtasks
```

## Output
`PLAN.md` in project root with all tasks, ready for `prg plan --from-design DESIGN.md`.

## Anti-Patterns
❌ Vague task descriptions
❌ Tasks without test criteria
❌ Missing file paths
❌ Tasks that take > 10 minutes
❌ Unclear dependencies

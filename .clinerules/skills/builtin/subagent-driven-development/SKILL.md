---
name: subagent-driven-development
description: |-
  When the user approves a plan and wants to execute it.
  When the user says "execute the plan" or "let's go" or "start implementation".
  When a PLAN.md exists and is ready to be executed task-by-task.
tools:
  - read
  - exec
  - edit
---

# Skill: Subagent-Driven Development

## Purpose
Without task isolation, a single agent accumulates context across all tasks — leading to context bleed, hallucinations from earlier tasks, and difficult-to-debug failures. This skill prevents that by dispatching a fresh subagent per task with two-stage review before committing each result.

## Auto-Trigger
- PLAN.md exists and user approves execution
- User says: "Execute the plan", "Let's go", "Start implementation"
- After `prg plan` generates a task list

## Process

### 1. Dispatch Subagent
Isolate each task so earlier context cannot corrupt later work.
Give the subagent: task description, relevant files, testing requirements — no knowledge of other tasks.

### 2. Subagent Executes
Let the subagent implement, write tests, and return code + test results before any review.

### 3. Stage 1 — Spec Compliance
Reject before checking quality; a non-compliant implementation wastes quality review time.
✓ Does it match task requirements?
✓ Are all files modified as specified?
✓ Do tests pass?
❌ If no → reject, provide feedback, retry

### 4. Stage 2 — Code Quality
✓ Follows project conventions?
✓ Handles edge cases?
✓ No obvious bugs?
✓ Code is readable?
❌ If no → request improvements

### 5. Commit and Report
Commit after each task so failures are isolated and rollback is cheap.
```bash
git add <files>
git commit -m "Task N: brief description"
```
✅ Task 1: Setup database schema (3min)
🔄 Task 2: In progress...

### Stopping Conditions
- All tasks complete
- Critical issue found (escalate to user)
- Subagent fails 3 times (escalate)

## Output
Each task produces: committed code, passing tests, and a progress entry in the session log.

## Anti-Patterns
❌ Giving subagent entire codebase context
❌ Skipping Stage 1 review
❌ Continuing after failed tests
❌ Not committing after each task

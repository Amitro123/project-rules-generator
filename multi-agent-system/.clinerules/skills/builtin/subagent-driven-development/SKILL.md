# Skill: Subagent-Driven Development

## Purpose
Execute implementation plan by dispatching fresh subagents per task, with two-stage review.

## Auto-Trigger
- PLAN.md exists and user approves execution
- User says: "Execute the plan", "Let's go", "Start implementation"

## Process

### For Each Task in PLAN.md:

#### 1. Dispatch Subagent
Create fresh context with:
- Task description only
- Relevant files
- Testing requirements
- NO knowledge of other tasks

#### 2. Subagent Executes
- Implements the task
- Writes/runs tests
- Returns code + test results

#### 3. Two-Stage Review

**Stage 1: Spec Compliance**
✓ Does it match task requirements?
✓ Are all files modified as specified?
✓ Do tests pass?
❌ If no → reject, provide feedback, retry

**Stage 2: Code Quality**
✓ Follows project conventions?
✓ Handles edge cases?
✓ No obvious bugs?
✓ Code is readable?
❌ If no → request improvements

#### 4. Commit
```bash
git add [files]
git commit -m "Task N: [brief description]"
```

### 5. Report Progress
✅ Task 1: Setup database schema (3min)
✅ Task 2: Create API endpoint (4min)
🔄 Task 3: In progress...

### Stopping Conditions
- All tasks complete
- Critical issue found (escalate to user)
- Subagent fails 3 times (escalate)

## Anti-Patterns
❌ Giving subagent entire codebase context
❌ Skipping Stage 1 review
❌ Continuing after failed tests
❌ Not committing after each task

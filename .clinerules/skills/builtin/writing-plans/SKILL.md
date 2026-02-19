# Skill: Writing Implementation Plans

## Purpose
Break approved designs into bite-sized, executable tasks (2-5 minutes each).

## Auto-Trigger
- After design approval (DESIGN.md exists)
- User says: "Let's implement this", "Create a plan"
- Before starting implementation

## Process

### Task Structure
Each task must include:
1. **Goal**: One-sentence objective
2. **Files**: Exact paths to modify/create
3. **Changes**: Specific code snippets or logic
4. **Tests**: How to verify it works
5. **Dependencies**: Which tasks must complete first

### Task Size Guidelines
✅ 2-5 minutes per task
✅ Single responsibility
✅ Independently testable
❌ "Refactor the entire module" (too big)
❌ "Add a comment" (too small)

### Plan Format
Task 1: [Title]
Dependencies: [Task IDs or "None"]
Files: [exact paths]
Changes:

[specific change 1]

[specific change 2]
Tests: [how to verify]
Estimated time: [X min]

## Output
Create `PLAN.md` in project root with all tasks.

## Anti-Patterns
❌ Vague task descriptions
❌ Tasks without test criteria
❌ Missing file paths
❌ Tasks that take > 10 minutes
❌ Unclear dependencies

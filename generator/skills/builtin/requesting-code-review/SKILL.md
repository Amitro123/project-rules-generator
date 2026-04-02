---
name: requesting-code-review
description: |-
  When the user says they are ready for review or wants to create a PR.
  When the user asks to check if code is ready for review.
  When the task or feature is complete and needs quality validation.
tools:
  - read
  - exec
---

# Skill: Requesting Code Review

## Purpose
Without a pre-review checklist, it is easy to forget debug statements, skipped tests, or missing context — causing avoidable review cycles and wasted reviewer time. This skill ensures code is genuinely ready before asking for human review.

## Auto-Trigger
- Task/feature complete
- User says: "Ready for review", "Can you review?"
- Before creating PR/merge request

## Process

### 1. Self-Review
Run a diff to read every line changed before anyone else does.
```bash
git diff main...HEAD
```
- ✓ Remove debug statements
- ✓ Check for commented-out code
- ✓ Verify no secrets/credentials

### 2. Tests
Verify the test suite is clean — reviewers should not discover broken tests.
- ✓ All tests pass locally
- ✓ New tests for new features
- ✓ Edge cases covered
- ✓ No skipped/ignored tests without reason

### 3. Code Quality
Catching style issues before review keeps feedback focused on logic, not formatting.
- ✓ Follows project style guide
- ✓ Functions < 50 lines
- ✓ No unresolved task markers without ticket reference
- ✓ Docstrings for public APIs

### 4. Documentation
- ✓ README updated if needed
- ✓ API docs updated
- ✓ CHANGELOG.md entry added
- ✓ Comments explain "why", not "what"

### 5. Dependencies
- ✓ No unnecessary dependencies added
- ✓ If new deps: justify in PR description
- ✓ Lock file updated

### 6. Performance
- ✓ No obvious performance issues
- ✓ Database queries optimized
- ✓ No N+1 queries

### 7. Security
- ✓ No SQL injection vectors
- ✓ User input sanitized
- ✓ Authentication/authorization checked
- ✓ No sensitive data in logs

## Output
```markdown
## Code Review Self-Assessment

### Changes Summary
Brief description of what changed and why.

### Checklist
- [✓] All tests pass
- [✓] No debug code
- [✓] Documentation updated

### Risks/Notes
Any concerns or open questions.

### Files Changed
- src/auth.py (+45, -12)

Ready for review: **YES** ✓
```

## Anti-Patterns
❌ Requesting review without running tests
❌ Not reviewing your own code first
❌ Missing context in PR description

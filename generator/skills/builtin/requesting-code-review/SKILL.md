# Skill: Requesting Code Review

## Purpose
Ensure code quality through pre-review checklist before asking for human review.

## Auto-Trigger
- Task/feature complete
- User says: "Ready for review", "Can you review?"
- Before creating PR/merge request

## Pre-Review Checklist

### 1. Self-Review
```bash
git diff main...HEAD
```
- ✓ Read every line you changed
- ✓ Remove debug statements
- ✓ Check for commented-out code
- ✓ Verify no secrets/credentials

### 2. Tests
- ✓ All tests pass locally
- ✓ New tests for new features
- ✓ Edge cases covered
- ✓ No skipped/ignored tests without reason

### 3. Code Quality
- ✓ Follows project style guide
- ✓ Functions < 50 lines
- ✓ No TODO/FIXME without ticket reference
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

## Review Report Format
```markdown
## Code Review Self-Assessment

### Changes Summary
[Brief description]

### Checklist
- [✓] All tests pass
- [✓] No debug code
- [✓] Documentation updated

### Risks/Notes
[Any concerns or TODOs]

### Files Changed
- [file] (+lines, -lines)

Ready for review: **YES** ✓
```

## Anti-Patterns
❌ Requesting review without running tests
❌ Not reviewing your own code first
❌ Missing context in PR description

---
name: analyze-code
description: |-
  When the user wants to analyze or check code quality.
  When the user wants to lint the codebase.
  When the user asks to check the project for quality issues.
tools:
  - read
  - search
  - exec
---

# Skill: Analyze Code

## Purpose
Without regular code analysis, quality issues accumulate silently — lint violations, dead code, and style drift that make future changes harder and riskier. This skill runs a structured analysis pass to surface issues before they compound.

## Auto-Trigger
- User says: "analyze code", "check quality", "lint the project"
- Before a PR or release cut
- After a large refactor

## Process

### 1. Run Static Analysis
Start with automated tools to get an objective baseline before any manual review.
```bash
prg analyze .
```
Or run the linter stack directly:
```bash
ruff check .
black --check .
mypy .
```

### 2. Review Output by Severity
Focus on errors and warnings first; suggestions are optional.
- **Errors**: Must fix before merging
- **Warnings**: Fix unless there is a documented reason to suppress
- **Suggestions**: Address in a follow-up or refactor

### 3. Check for Dead Code
```bash
# Python projects
python -m py_compile **/*.py && echo "No syntax errors"
```

### 4. Summarize Findings
Group issues by file and category so the developer can prioritize the fix order.

## Output
Quality report with:
- Issue count by severity
- Top offending files
- Actionable fix suggestions per issue

## Anti-Patterns
❌ Suppressing warnings without a comment explaining why
❌ Fixing style issues without running tests afterward
❌ Analyzing only changed files — issues in unchanged files still matter

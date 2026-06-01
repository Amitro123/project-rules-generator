---
name: code-review
description: |
  Systematic code review workflow — evaluate changes for correctness, style,
  security, and test coverage before merging.
  When the user asks to review code or a pull request.
  When the user says "check code quality" or "look over this diff".
  When the user requests feedback on changes before merging.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
metadata:
  tags: [code-review, quality, testing, security, best-practices]
---

# Skill: Code Review

## Purpose

Ad-hoc review catches obvious bugs but misses entire categories of issues
(untested edge cases, security gaps, style drift). A structured checklist
ensures every review covers correctness, style, security, and test coverage
consistently — regardless of who is doing the review.

## Auto-Trigger

Activate when the user says:
- **"review this code"** / **"review my changes"**
- **"perform a code review"** / **"check code quality"**
- **"feedback on this PR"** / **"look over this diff"**

Do NOT activate for: "write code", "debug an error", "explain this function"

## CRITICAL

- Never approve code with failing tests or linter errors.
- Flag security issues (hardcoded secrets, SQL injection, missing auth) as
  blockers — do not leave them as suggestions.
- Be specific: reference file name and line number for every finding.

## Process

### 1. Understand the scope

```bash
# See what changed
git diff main...HEAD --stat
git diff main...HEAD
```

### 2. Run tests and linters

```bash
# Tests must pass before review findings are meaningful
pytest -x -q

# Style / type checks (use whatever the project has)
ruff check .
black --check .
mypy .
```

### 3. Review correctness

Check manually for:
- Logic errors and off-by-one mistakes
- Unhandled error paths and missing fallbacks
- Incorrect assumptions about input types or ranges
- Race conditions in async or threaded code

### 4. Review security

Check manually for:
- Hardcoded credentials or API keys
- Unsanitised user input passed to shell, SQL, or eval
- Missing authentication / authorisation on new endpoints
- Sensitive data written to logs

### 5. Review style and maintainability

Check manually for:
- Functions longer than ~40 lines (split candidates)
- Duplicated logic that should be extracted
- Variable names that don't convey intent
- Missing or outdated docstrings on public interfaces

### 6. Check test coverage

```bash
pytest --cov --cov-report=term-missing -q
```

New code paths that aren't exercised by tests are a finding.

### 7. Summarise findings

Group findings by severity:

| Severity | Meaning |
|----------|---------|
| **BLOCKER** | Must fix before merge (failing test, security issue, crash) |
| **MAJOR** | Should fix before merge (logic error, missing error handling) |
| **MINOR** | Fix if easy, otherwise track (style, naming, small refactor) |
| **NIT** | Optional polish (whitespace, comment wording) |

## Validate

```bash
# After the author addresses findings, re-run the full suite
pytest -q
ruff check .
```

## Output

- Structured list of findings with severity, file, line, and suggested fix
- Explicit APPROVED / CHANGES REQUESTED verdict
- List of tests that should be added if coverage is insufficient

## Anti-Patterns

❌ Vague feedback: "This looks wrong" — always say *why* and *what* to do instead.

❌ Blocking on style nits while missing a logic error — triage by severity first.

❌ Reviewing without running the tests — a passing test suite is the baseline.

✅ One finding per comment, with file + line reference.

✅ Separate blockers from suggestions so the author knows what to fix now vs later.

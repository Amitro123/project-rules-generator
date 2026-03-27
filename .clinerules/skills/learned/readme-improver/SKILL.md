---
name: readme-improver
description: |
  Audits and rewrites README.md for a Python CLI project. Fixes stale data (badge counts,
  versions), improves quick-start accuracy, restructures sections for scanability, and
  ensures every command example is runnable as-is. Activate when user says "improve readme",
  "fix readme", "update readme", or "readme is outdated".
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  author: PRG
  version: 1.0.0
  category: learned
  tags: [readme, documentation, python, cli]
---

# Skill: README Improver

## Purpose

Audit and rewrite `README.md` for accuracy, clarity, and scanability. Focus on:
- Fixing stale numbers (test counts, versions, badges)
- Verifying every command example actually runs
- Restructuring sections so the most important info is first
- Removing outdated change-log noise from the main README

## Auto-Trigger

Activate when user requests:
- **"improve readme"**
- **"fix readme"**
- **"update readme"**
- **"readme is outdated"**
- **"readme needs work"**

## CRITICAL

- Read the current README before proposing any edits
- Run `pytest --tb=no -q` to get the real test count before updating the badge
- Run `prg --version` (or `python -m main --version`) to confirm the version string
- Never invent commands — verify each example actually exists in the CLI
- Keep the tone neutral and factual; remove marketing hyperbole

## Process

### 1. Audit current README

```bash
# Get real test count
pytest --tb=no -q 2>&1 | tail -2

# Get real version
python -m main --version

# List all available commands
python -m main --help
```

Check each section against:
- [ ] Badge numbers are current
- [ ] Quick Start command matches the real CLI entry point
- [ ] All `prg` / `python -m main` examples are syntactically correct
- [ ] Section order: badges → pitch → quick-start → install → usage → architecture → contributing
- [ ] No stale `Recent Changes` section in main README (belongs in CHANGELOG.md)
- [ ] Contributing section references code standards and test commands

### 2. Fix stale data

Update any outdated values:
- Test count badge → real number from pytest output
- Version strings → from `--version` flag
- Model names → current models (not deprecated ones)

### 3. Restructure for scanability

Ideal section order for a CLI tool README:
1. Title + badges
2. One-line pitch (what it does)
3. **Quick Start** (runnable in < 60 seconds)
4. Installation
5. AI Providers table
6. Usage (grouped by use case, not flag)
7. How It Works / Architecture
8. Contributing
9. *(move Recent Changes → CHANGELOG.md)*

### 4. Verify examples

For each code block in the README:
- Does the command exist (`python -m main <cmd> --help`)?
- Are the flags correct?
- Is the output description accurate?

### 5. Write and verify

Apply edits with the Edit tool. After writing, re-read the file to confirm no
formatting artifacts (stray `│` characters, broken code fences, duplicate sections).

## Output

- Updated `README.md` with corrected badges, accurate commands, clean structure
- Brief summary of every change made and why

## Anti-Patterns

❌ Inventing command flags that don't exist
✅ Verify each flag with `--help` before documenting

❌ Keeping a `Recent Changes` section in README that duplicates CHANGELOG.md
✅ Link to CHANGELOG.md and remove the inline version history

❌ Updating badge numbers from memory
✅ Run `pytest` and read the actual output

❌ Rewriting the whole README when only 3 things are stale
✅ Make surgical edits — smallest diff that fixes the problems

## Examples

```bash
# Step 1: audit
pytest --tb=no -q 2>&1 | tail -2
python -m main --help

# Step 2: check a specific command exists
python -m main analyze --help | grep "\-\-create-skill"

# Step 3: apply fixes
# (use Edit tool for targeted replacements)
```

---
name: readme-improvement
description: |
  Audits and rewrites README.md for the Project Rules Generator project.
  Fixes stale data, adds missing features from docs/, corrects skill routing
  descriptions (project/ vs learned/), and ensures every command is runnable.
  Activate when user says "improve readme", "update readme", "readme needs work".
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
triggers:
  - "improve readme"
  - "update readme"
  - "fix readme"
  - "readme needs work"
  - "readme is outdated"
metadata:
  tags: [readme, documentation, python, cli, prg]
---

# Skill: README Improvement (PRG Project)

## Purpose

Audit and rewrite `README.md` for accuracy, completeness, and scanability,
using `docs/` as the authoritative reference for features, commands, and
architecture. Keep edits surgical — fix what is wrong, add what is missing,
remove what is stale.

## Auto-Trigger

Activate when user requests:
- **"improve readme"**
- **"update readme"**
- **"fix readme"**
- **"readme needs work"**
- **"readme is outdated"**

Do NOT activate for: "improve code quality", "update dependencies", "fix tests"

## CRITICAL

- Always read current `README.md` AND the relevant `docs/` files before editing
- Run `pytest --tb=no -q 2>&1 | tail -2` to get the real test count for the badge
- Run `prg --version` to confirm the version string
- Verify every CLI example with `prg <cmd> --help` before documenting it
- The skill routing section MUST reflect the current design:
  - `--create-skill` writes to `skills/project/` (project-specific, AI-generated with project context)
  - README auto-flow (`--from-readme`) writes to `skills/learned/` (reusable tech-pattern skills)

## Process

### 1. Audit current README against docs/

```bash
# Get real test count for badge
pytest --tb=no -q 2>&1 | tail -2

# Get current version
prg --version

# List all top-level commands to verify Usage section
prg --help
```

Cross-check each README section against its docs/ source:

| README section | Authoritative source |
|---------------|---------------------|
| Features list | `docs/features.md` |
| Quick Start | `docs/quick-start.md` |
| CLI commands | `docs/cli.md` |
| Skills explanation | `docs/skills.md` |
| Architecture diagram | `docs/architecture.md` |
| Workflows | `docs/workflows.md` |

Audit checklist:
- [ ] Badge test count matches real pytest output
- [ ] Quick Start uses `prg init .` (first-run wizard) not just `prg analyze .`
- [ ] Features list covers all 9 features from `docs/features.md`
- [ ] Skill routing section reflects `project/` vs `learned/` correctly
- [ ] All `prg` command examples are syntactically correct
- [ ] No stale "Recent Changes" inline — belongs in `CHANGELOG.md`
- [ ] AI provider table uses current model names from `docs/cli.md`

### 2. Fix stale data

```bash
pytest --tb=no -q 2>&1 | tail -1
prg --version
```

Update badge test count and provider model names.

### 3. Add missing content from docs/

Features commonly missing from README but documented in docs/:
- `prg init .` first-run wizard (`docs/quick-start.md`)
- `prg design "..."` two-stage design before plan (`docs/features.md`)
- Skill routing: `--create-skill` to `project/`, README flow to `learned/`
- The three skill layers: `project/` > `learned/` > `builtin/`

### 4. Restructure for scanability

Ideal section order for a CLI tool README:
1. Title + badges
2. One-line pitch
3. Quick Start (under 60 seconds to first output)
4. Installation
5. AI Providers table
6. Usage (grouped by use case, not by flag)
7. How It Works (skill routing, output structure)
8. Contributing

### 5. Apply edits and verify

Use the `Edit` tool for surgical replacements. After editing, confirm:
```bash
# Check no broken fences or formatting artifacts
grep -n "^\`\`\`" README.md | head -20
# Confirm skill routing section is correct
grep -n "project/\|learned/" README.md
```

## Output

- Updated `README.md` with correct badge count, accurate skill routing,
  all features from `docs/features.md`, and every CLI example verified
- Brief change summary listing what was fixed and why

## Anti-Patterns

❌ Updating badge numbers from memory
✅ Run `pytest --tb=no -q` and read the actual output

❌ Inventing command flags that do not exist
✅ Verify each flag with `prg <cmd> --help` before writing it

❌ Describing `--create-skill` as writing to `learned/`
✅ `--create-skill` writes to `skills/project/`; README flow writes to `skills/learned/`

❌ Rewriting the whole README when only a few things are stale
✅ Surgical edits — smallest diff that fixes the real problems

❌ Keeping inline version history in README
✅ Link to `CHANGELOG.md` and remove duplicate history

## Examples

```bash
# Audit step
pytest --tb=no -q 2>&1 | tail -2
prg --version
prg --help

# Verify a specific command exists
prg analyze --help | grep "\-\-create-skill"
prg analyze --help | grep "\-\-from-readme"

# Check current skill routing section in README
grep -n "project/" README.md
grep -n "learned/" README.md
```

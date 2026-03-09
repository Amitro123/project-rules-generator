# Skills Guide

Skills are reusable AI-agent instructions stored as `SKILL.md` files.
They teach the agent *when* to activate and *how* to behave.

## Skill Anatomy

A valid `SKILL.md` has a YAML frontmatter block followed by a body:

```markdown
---
description: |
  When the user asks to write pytest tests, add fixtures, or debug test failures.
  When the task involves test coverage or test-driven development.
allowed-tools:
  - Read
  - Edit
  - Bash
metadata:
  category: testing
  trigger_count: 2
---

# Pytest Testing Workflow

## When to Use
...

## Guidelines
...
```

### Required Frontmatter Fields

| Field | Description |
|-------|-------------|
| `description` | Trigger phrases starting with "When …". One per line. |
| `allowed-tools` | YAML list of tools the agent may use for this skill. |

### Optional Fields

| Field | Description |
|-------|-------------|
| `metadata` | Object with `category`, `trigger_count`, etc. |
| `version` | Semver string (e.g. `"1.0.0"`). |

---

## Skill Discovery

Skills are resolved from three layers (highest priority last):

| Layer | Location |
|-------|----------|
| **Builtin** | `~/.project-rules-generator/builtin/` |
| **Learned** | `~/.project-rules-generator/learned/` or `.clinerules/skills/learned/` |
| **Project** | `.clinerules/skills/project/` |

Project skills override learned, which override builtin.

---

## CLI Commands

### List all skills

```bash
prg skills list .
```

Shows a table with name, layer, trigger count, allowed tools, and whether
valid frontmatter was found.

Add `--all` to also include builtin skills from `~/.project-rules-generator`.

### Validate a skill

```bash
prg skills validate <name> [PATH]
```

Runs 7 checks:
1. YAML frontmatter present
2. `description` field present and non-empty
3. `allowed-tools` field present and non-empty
4. At least one `When …` trigger phrase in description
5. `allowed-tools` is a YAML list (not a plain string)
6. `metadata` block present (optional, recommended)
7. Body content after frontmatter

Exits 0 if all checks pass, 1 if any fail.

### Inspect a skill

```bash
prg skills show <name> [PATH]
```

Renders the frontmatter as a grid table and the body as a panel.

---

## Generating Skills

### From README (automatic)

`prg analyze .` auto-generates skills based on your tech stack.
With `--mode ai` it uses an LLM to write skill bodies:

```bash
prg analyze . --mode ai --auto-generate-skills
```

### Create manually

```bash
prg analyze . --create-skill my-workflow
```

Creates `.clinerules/skills/learned/my-workflow/SKILL.md` and refreshes
`auto-triggers.json`.

---

## Trigger Evaluation

The `TriggerEvaluator` tests which skill fires for a given query:

```bash
prg agent "I need to refactor some tests"
# Output: systematic-debugging  (or whichever skill matches)
```

This lets you verify your trigger phrases are precise before deploying.

---

## File Layout

```
.clinerules/
  rules.md              ← coding rules
  auto-triggers.json    ← trigger index for fast matching
  skills/
    learned/
      pytest-testing/
        SKILL.md        ← learned skill
    project/
      my-workflow/
        SKILL.md        ← project-specific override
    builtin/            ← symlink to ~/.project-rules-generator/builtin
```

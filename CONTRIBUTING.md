# Contributing to project-rules-generator

## Setup

```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e ".[llm]"
pip install -r requirements-dev.txt
```

## Running tests

```bash
pytest                                  # all tests
pytest --cov=generator --cov=prg_utils  # with coverage
black . && ruff check . && isort .      # format/lint (must pass before commit)
```

## Project layout

```
cli/           CLI commands (one file per command: cmd_design.py, cmd_plan.py, …)
generator/     Core business logic
  ai/          AI client factory and provider adapters
  planning/    Task decomposition and plan parsing
  skills/      Built-in skill files (Markdown + YAML frontmatter)
  utils/       Tech detection, quality checks, README bridge
prg_utils/     Shared utilities not tied to the generator
tests/         pytest test suite
```

## Adding a new CLI command

1. Create `cli/cmd_<name>.py` with a `@click.command(name="<name>")` function.
2. Import and register it in `cli/cli.py` (follow the existing pattern).
3. Update both the `@click.option` decorator **and** the function signature when adding options.
4. Write tests in `tests/test_cmd_<name>.py`.

## How the skill system works

Skills are Markdown files with YAML frontmatter. Three layers (lowest-to-highest priority):

| Layer   | Location                              | Created by         |
|---------|---------------------------------------|--------------------|
| builtin | `generator/skills/builtin/`           | shipped with PRG   |
| learned | `~/.project-rules-generator/learned/` | `prg analyze`      |
| project | `.clinerules/skills/project/`         | `prg analyze`      |

`SkillsManager` (in `generator/skills_manager.py`) is the single entry point for all skill operations. Use `sm.list_skills()`, `sm.resolve_skill(name)`, etc.

### Canonical skill shape

A skill is a **directory** containing one `SKILL.md` file:

```
my-skill/
└── SKILL.md
```

Loose `my-skill.md` files at the top of a skill scope are supported for backward compatibility but are deprecated — the directory form is canonical and new skills must use it.

### Canonical frontmatter

```yaml
---
name: my-skill                    # lowercase, hyphenated, matches directory
description: |                    # YAML block scalar, multi-line
  One full sentence explaining what the skill does and why it matters.
  When the user mentions "foo", "bar", "baz".
  When the user needs help with my-skill.
  Do NOT activate for "unrelated-thing", "off-topic".
license: MIT
allowed-tools:                    # YAML list, not a quoted string
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  author: PRG
  version: 1.0.0
  category: project
  tags: [python, testing, my-tag]
---
```

Rules:

1. **Description** is a YAML block scalar (`description: |`). First line is a full-sentence explanation (≥ 40 chars). Subsequent `When ...` lines are the machine-readable triggers — agents decide when to activate by matching these. End with a `Do NOT activate for ...` line to reduce false positives.
2. **`allowed-tools`** is a YAML list. Legacy skills may use `tools:` (alias) or a quoted space-separated string — the parser accepts both but lints warn on the string shape.
3. **Triggers** live inside `description` (`When the user ...`). Older skills may have a top-level `auto_triggers:` dict with `keywords:` and `project_signals:` lists — the parser flattens both shapes, but new skills should put triggers in the description.
4. **Name** must be lowercase, hyphenated, and must **not** start with `temp-`, `tmp-`, `scratch-`, `placeholder-`, or `draft-` — the generator refuses these prefixes so scratch files never ship.

Run `pytest tests/test_quality_checker_triggers.py` after adding a skill to confirm the quality check still passes.

## Offline vs AI-enabled commands

| Command       | Offline | Requires API key |
|---------------|---------|------------------|
| `prg init`    | yes     | no               |
| `prg analyze` | yes     | no               |
| `prg design`  | no      | yes              |
| `prg plan`    | no      | yes              |
| `prg review`  | no      | yes              |

Set `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, or `OPENAI_API_KEY` to enable AI commands.

## Writing tests

- Tests live in `tests/`; use `pytest` with `tmp_path` fixtures for file operations.
- When testing `ContentAnalyzer` file ops, pass `allowed_base_path=tmp_path`.
- When testing LLM prompt functions, provide a **complete** input dict to avoid `KeyError`.
- Verify mock targets match actual import paths before asserting calls.
- Remove tests for deleted features immediately — no ghost tests.

## Commit style

```
<type>: <short description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

## Pull requests

- One feature or fix per PR.
- All tests must pass and formatters must be clean.
- Describe what changed and why in the PR body.

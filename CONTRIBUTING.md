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

# CLI Reference

## Main Command

```bash
prg analyze [PROJECT_PATH] [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `[PROJECT_PATH]` | argument | `.` (current dir) | The root directory of the project to analyze. |
| `--output` | dir | `.clinerules/` | Custom output directory for generated rules. |
| `--mode` | choice | `manual` | Analysis mode: `manual` (fast, local), `ai` (deep, requires key), `constitution` (principles only). |
| `--incremental` | flag | `false` | Only regenerate sections that have changed (much faster). |
| `--constitution` | flag | `false` | Generate `constitution.md` with high-level principles. |
| `--auto-generate-skills` | flag | `false` | Enable AI skill matching and generation (requires `--ai`). |
| `--ai` | flag | `false` | Use AI (LLM) for analysis. Implies `--mode ai`. |
| `--api-key` | str | `env` | Gemini/Claude API key. Can be set via `GEMINI_API_KEY` env var. |
| `--list-skills` | flag | `false` | List all available skills (builtin + learned). |
| `--add-skill` | str | - | Add a skill by name (e.g., `builtin/debugging`) or file path. |
| `--remove-skill` | str | - | Remove a skill from the project configuration. |
| `--merge` | flag | `false` | Merge new rules with existing files instead of overwriting. |
| `--no-commit` | flag | `false` | Skip the automatic git commit of `.clinerules` changes. |
| `--verbose` | flag | `false` | Enable detailed output for debugging. |

## Secondary Commands

### Design

Generate an architectural design for a feature.

```bash
prg design <TASK_DESCRIPTION> [OPTIONS]
```

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--output` | file | `DESIGN.md` | Output file path. |
| `--api-key` | str | `env` | AI API key. |

### Plan

Break down a task into smaller subtasks.

```bash
prg plan <TASK_DESCRIPTION> [OPTIONS]
```

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--output` | file | `PLAN.md` | Output file path for the plan. |
| `--from-design` | file | - | Generate tasks from an existing `DESIGN.md` file. |
| `--api-key` | str | `env` | AI API key for the planning agent. |

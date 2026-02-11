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
| `--quality-check` 🆕 | flag | `false` | Score generated files (0-100) across 5 quality criteria. |
| `--auto-fix` 🆕 | flag | `false` | Automatically improve files scoring below 85. Requires `--quality-check`. |
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
| `[TASK_DESCRIPTION]` | argument | - | Task to plan (e.g., "Add Redis cache"). Optional if using `--from-design` or `--from-readme`. |
| `--output` | file | auto | Output file path for the plan. Defaults to `PLAN.md` or `PROJECT-ROADMAP.md`. |
| `--from-design` | file | - | Generate tasks from an existing `DESIGN.md` file. |
| `--from-readme` 🆕 | file | - | Generate project roadmap from `README.md` features. |
| `--status` 🆕 | flag | `false` | Show progress on existing plan files with visual progress bars. |
| `--interactive` | flag | `false` | Open files in IDE as tasks are listed. |
| `--auto-execute` | flag | `false` | Automatically create files and open them (requires `--interactive`). |
| `--api-key` | str | `env` | AI API key for the planning agent. |
| `--provider` | choice | auto | AI provider: `gemini` or `groq`. Auto-detected from API key if not specified. |

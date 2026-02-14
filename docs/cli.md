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
| `--eval-opik` 🆕 | flag | `false` | Log generation traces to Comet Opik (requires `OPIK_API_KEY`). |
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

## Task Automation 🆕

Reduce cognitive load by letting the agent manage the task lifecycle.

### `prg start`

Runs the **full workflow** from idea to execution readiness.

```bash
prg start "Refactor auth middleware to use JWT"
```

**Steps:**
1.  **Plan**: Generates `PLAN.md` using the Two-Stage Planning agent.
2.  **Tasks**: Breaks plan into `tasks/001-init.md`, `tasks/002-impl.md`, etc.
3.  **Preflight**: Checks for missing dependencies or potential conflicts.
4.  **Auto-Fix**: Attempts to fix preflight issues automatically.
5.  **Ready**: Prepares the environment for the first task.

### `prg setup`

Same as `start`, but stops after generating tasks. Useful if you want to inspect manual work before execution.

```bash
prg setup "Refactor auth middleware"
```

### `prg exec`

Execute, complete, or skip a specific task file.

```bash
# Execute a task (opens context, sets up instructions)
prg exec tasks/001-setup-jwt.md

# Mark a task as complete manually
prg exec tasks/001-setup-jwt.md --complete

# Skip a task
prg exec tasks/001-setup-jwt.md --skip
```

### `prg status`

Shows a high-level progress table of the current sprint.

```bash
prg status
```

**Output:**
- Reads from `TASKS.yaml` (new format) or falls back to parsing `PLAN.md`.
- Displays: Task ID, Status (Pending/In Progress/Done), Description.

## Agent Commands

### `prg agent`

Simulate the auto-trigger matching engine.

```bash
prg agent "I need to fix a bug"
```

**Output:**
```
🎯 Auto-trigger: systematic-debugging
```

**Use Case:**
Verify which skill will be selected for a given user query. Useful for debugging triggers or integrating PRG into other agent loops.


### `prg leaderboard`

Open the Comet Opik dashboard to check quality metrics.

```bash
prg leaderboard
```

**Output:**
Opens `https://www.comet.com/opik/dashboard` in your default browser.


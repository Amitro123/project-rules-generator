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

### Create Skills

Generate high-quality, context-aware skills for your project.

```bash
prg create-skills [PROJECT_PATH] [OPTIONS]
```

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `[PROJECT_PATH]` | argument | `.` (current dir) | The root directory of the project. |
| `--skill` | str | - | Generate a specific skill by name (e.g., `fastapi-security`). |
| `--quality-threshold` | int | `70` | Minimum quality score (0-100) required to save the skill. |
| `--export-report` | flag | `false` | Save a JSON quality report for each generated skill. |
| `--verbose` | flag | `false` | Show detailed generation logs and quality issues. |
| `--ai` | flag | `false` | Use AI to enhance skill generation (requires API key). |


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

Runs the **fast workflow** from idea to execution readiness.

```bash
prg start "Refactor auth middleware to use JWT"
```

**Steps:**
1.  **Plan**: Generates `PLAN.md` using the Two-Stage Planning agent.
2.  **Tasks**: Breaks plan into `tasks/001-init.md`, `tasks/002-impl.md`, etc.
3.  **Preflight**: Checks for missing dependencies or potential conflicts.
4.  **Auto-Fix**: Attempts to fix preflight issues automatically.
5.  **Ready**: Prepares the environment for the first task.

### `prg autopilot` 🆕

Full end-to-end autonomous orchestration. Unlike `start`, `autopilot` manages the discovery phase and the execution loop automatically.

```bash
prg autopilot [PROJECT_PATH] [OPTIONS]
```

**Workflow:**
1.  **Discovery**: Automatically runs `analyze`, `plan`, and `tasks`.
2.  **Branching**: Creates a git branch for each task (`autopilot/task-{id}`).
3.  **Autonomous Agent**: Uses a task agent to generate code changes.
4.  **Approval**: Prompts the user for approval before merging changes.
5.  **Cleanup**: Merges branch and deletes it on pass; rolls back on failure/rejection.

**Options:**
- `--discovery-only`: Stop after rule generation and task creation.
- `--execute-only`: Assume tasks exist and start execution loop.
- `--provider`: AI provider (`gemini`, `groq`).
- `--api-key`: API key for the agent.

- `--provider`: AI provider (`gemini`, `groq`).
- `--api-key`: API key for the agent.

### `prg manager` 🆕

Complete 4-phase project lifecycle orchestration.

```bash
prg manager [PROJECT_PATH] [OPTIONS]
```

**Phases:**
1.  **Setup**: Automatically generates missing artifacts (`rules.md`, `PLAN.md`, `spec.md`, `ARCHITECTURE.md`, `PROJECT-MANAGER.md`).
2.  **Verify**: Runs pre-flight checks to ensure system readiness.
3.  **Copilot**: Runs the implementation loop (same as `autopilot` with checkpoints).
4.  **Summary**: Generates a completion report with metrics.

**Options:**
- `--provider`: AI provider (`gemini`, `groq`).
- `--api-key`: API key for the agent.

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


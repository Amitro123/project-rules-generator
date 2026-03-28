# CLI Reference

## Provider Auto-Detection

PRG resolves the AI provider automatically from environment variables.
Priority order: **Anthropic → OpenAI → Gemini → Groq (default)**.

```bash
export ANTHROPIC_API_KEY=sk-ant-...  # https://console.anthropic.com
export OPENAI_API_KEY=sk-...         # https://platform.openai.com
export GEMINI_API_KEY=...            # https://aistudio.google.com
export GROQ_API_KEY=gsk_...          # https://console.groq.com
```

API key prefixes are also detected automatically:
- `sk-ant-...` → Anthropic
- `sk-...` → OpenAI
- `gsk_...` → Groq

If no keys are set, commands fall back to README-only mode (no LLM required).

See [llm-router.md](llm-router.md) for full routing configuration.

---

## `prg init` — First-Run Wizard

```bash
prg init [PROJECT_PATH] [OPTIONS]
```

Detects project stack, checks API keys, generates initial `rules.md`, and
prints actionable next steps. The recommended starting point for new projects.

| Flag | Default | Description |
|------|---------|-------------|
| `PROJECT_PATH` | `.` | Project root directory |
| `--yes / -y` | false | Skip confirmation prompts |
| `--provider` | auto | Force `gemini`, `groq`, `anthropic`, or `openai` |

---

## `prg analyze` — Full Analysis

```bash
prg analyze [PROJECT_PATH] [OPTIONS]
```

Full pipeline: README parsing → rules → skills → clinerules.yaml → git commit.

| Flag | Default | Description |
|------|---------|-------------|
| `PROJECT_PATH` | `.` | Project root |
| `--mode` | `manual` | `manual` / `ai` / `constitution` |
| `--ai` | false | Enable LLM analysis |
| `--auto-generate-skills` | false | Match and generate skills with AI |
| `--constitution` | false | Generate `constitution.md` |
| `--incremental` | false | Skip unchanged sections |
| `--output DIR` | `.clinerules` | Output directory |
| `--provider` | auto | `gemini`, `groq`, `anthropic`, or `openai` |
| `--strategy` | `auto` | Routing strategy: `auto`, `speed`, `quality`, or `provider:<name>` |
| `--api-key` | env | Override env var key (auto-detects provider from prefix) |
| `--merge` | false | Keep existing skill files |
| `--commit / --no-commit` | true | Auto-commit generated files |
| `--quality-check` | false | Score files 0–100 |
| `--auto-fix` | false | Improve files below threshold (needs `--quality-check`) |
| `--create-rules` | false | Also run Cowork rules creator |
| `--list-skills` | false | List all skills then exit |
| `--create-skill NAME` | — | Create a new skill (destination set by `--scope`) |
| `--scope` | `learned` | Skill destination: `learned` (global reusable, default), `builtin` (universal patterns), `project` (this project only) |
| `--remove-skill NAME` | — | Remove a learned skill |
| `--verbose / --quiet` | true | Detailed output |

**`--strategy` values:**

| Value | Behaviour |
|-------|-----------|
| `auto` | Quality ÷ usage load-balance (default) |
| `quality` | Highest-quality provider first (anthropic → openai → gemini → groq) |
| `speed` | Fastest provider first (groq → gemini → openai → anthropic) |
| `provider:X` | Always use provider X |

```bash
# Strategy examples
prg analyze . --create-skill dom --ai --strategy quality
prg analyze . --create-skill dom --ai --strategy speed
prg analyze . --create-skill dom --ai --strategy provider:anthropic

# Scope examples
prg analyze . --create-skill mypy-type-errors --scope builtin   # universal pattern
prg analyze . --create-skill auth-flow --ai                     # reusable, default learned
prg analyze . --create-skill deploy-checklist --scope project   # this project only
```

---

## `prg create-rules` — Cowork Rules Creator

```bash
prg create-rules [PROJECT_PATH] [OPTIONS]
```

Generates high-quality, priority-scored rules using the Cowork pipeline.
Includes quality validation with conflict detection.

| Flag | Default | Description |
|------|---------|-------------|
| `PROJECT_PATH` | `.` | Project root |
| `--tech` | auto | Comma-separated tech stack (e.g. `fastapi,pytest,docker`) |
| `--quality-threshold` | `85` | Minimum score to accept (0–100) |
| `--output DIR` | `.clinerules` | Output directory |
| `--export-report` | false | Write `rules.quality.json` |
| `--verbose / -v` | false | Show warnings and full detail |

**Examples:**

```bash
prg create-rules .
prg create-rules . --tech "fastapi,pytest,docker"
prg create-rules . --quality-threshold 90 --verbose --export-report
```

---

## `prg skills` — Skill Management

```bash
prg skills COMMAND [OPTIONS]
```

### `prg skills list`

```bash
prg skills list [PATH] [--all]
```

Lists all `SKILL.md` files under `.clinerules/skills/`. Shows name, layer
(project/learned/builtin), trigger count, allowed tools, and frontmatter
status. Add `--all` to include global builtin skills.

### `prg skills validate`

```bash
prg skills validate <NAME_OR_PATH> [PATH]
```

Validates a skill against 7 checks. Exits 1 if any fail.

### `prg skills show`

```bash
prg skills show <NAME_OR_PATH> [PATH]
```

Pretty-prints a skill's frontmatter as a table and body as a panel.

See [skills.md](skills.md) for the full skill authoring guide.

---

## `prg plan` — Task Planning

```bash
prg plan <TASK_DESCRIPTION> [OPTIONS]
```

AI-powered task decomposition into subtasks.

| Flag | Default | Description |
|------|---------|-------------|
| `TASK_DESCRIPTION` | — | What to build |
| `--output` | `PLAN.md` | Output file |
| `--from-design FILE` | — | Generate from `DESIGN.md` |
| `--from-readme FILE` | — | Generate roadmap from `README.md` |
| `--status` | false | Show progress on existing plan |
| `--interactive` | false | Open files in IDE |
| `--provider` | auto | `gemini`, `groq`, `anthropic`, or `openai` |

---

## `prg design` — Architecture Design

```bash
prg design <TASK_DESCRIPTION> [OPTIONS]
```

Generates a `DESIGN.md` with problem statement, architecture decisions, API
contracts, data models, and success criteria.

---

## `prg start` — Fast Setup

```bash
prg start "Add Redis caching"
```

Plan → Tasks → Preflight → Auto-Fix → Ready. Generates `PLAN.md` and
`tasks/` directory, then reports the next task to run.

---

## `prg autopilot` — Autonomous Agent

```bash
prg autopilot [PROJECT_PATH] [OPTIONS]
```

Full autonomous loop: Analyze → Plan → Tasks → Branch → Implement → Verify →
Merge. Each task runs in its own git branch.

| Flag | Description |
|------|-------------|
| `--discovery-only` | Stop after rule generation and task creation |
| `--execute-only` | Skip discovery, run execution loop only |
| `--provider` | `gemini`, `groq`, `anthropic`, or `openai`. Auto-detected if omitted. |
| `--api-key` | Override env var key |

---

## `prg status` / `prg exec` / `prg next`

| Command | Description |
|---------|-------------|
| `prg status` | Show task progress table from `TASKS.yaml` or `PLAN.md` |
| `prg exec tasks/001-foo.md` | Execute / complete / skip a task |
| `prg next` | Print the next pending task |
| `prg query` | Query tasks by status |

---

## `prg agent` — Trigger Simulation

```bash
prg agent "I need to fix a bug in the auth module"
```

Simulates the auto-trigger engine to show which skill would activate for a
given query. Useful for testing trigger phrases.

---

## `prg manager` — Full Lifecycle

```bash
prg manager [PROJECT_PATH] [OPTIONS]
```

4-phase orchestration: Setup → Verify → Copilot → Summary. Generates all
missing artifacts before starting the execution loop.

| Flag | Description |
|------|-------------|
| `--provider` | `gemini`, `groq`, `anthropic`, or `openai`. Auto-detected if omitted. |
| `--api-key` | Override env var key |
| `--verbose/--quiet` | Verbose output (default: verbose) |

---

## `prg providers` — AI Provider Management

```bash
prg providers COMMAND [OPTIONS]
```

### `prg providers list`

Rich table of all 4 providers: name, status (✅ Ready / ❌ No key), quality score,
speed score, default model, and env variable.

```bash
prg providers list
```

### `prg providers test`

Send a test prompt to verify connectivity and print latency.

```bash
prg providers test                     # Test all providers with keys
prg providers test --provider anthropic  # Test a specific provider
```

### `prg providers benchmark`

Run N standard prompts, measure average latency, and rank by composite
quality/speed score. Prints a Rich table with the recommended provider.

```bash
prg providers benchmark                # 3 prompts (default)
prg providers benchmark --prompts 5   # More prompts for accuracy
```

See [llm-router.md](llm-router.md) for routing configuration and `~/.prg/ai_strategy.yaml` defaults.

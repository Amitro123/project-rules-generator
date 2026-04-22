---
name: agent-architecture-analyzer
description: |-
  Helps developers understand, extend, and debug the PRG agent system.
  When the user asks how the agent system works, how to add a new command, or how Ralph operates.
  When the user asks why auto-trigger matching is not working or returning wrong results.
  When the user wants to add a new skill trigger, extend the fallback trigger table, or tune synonym expansion.
  When the user wants to understand or modify the Ralph loop — thresholds, iteration steps, or exit conditions.
  When the user asks about skill routing, the two-pass trigger strategy, or AgentExecutor internals.
  Do NOT activate for general debugging ("bug", "error") — use systematic-debugging instead.
  Do NOT activate for "create a skill" or "add a skill" — those are for skill management commands.
license: MIT
allowed-tools:
  - Read
  - Grep
  - Bash
  - Write
  - Edit
metadata:
  author: PRG
  version: 1.0.0
  category: core
  tags: [agent, ralph, architecture, triggers, routing, prg]
---

# Skill: Agent Architecture Analyzer

## Purpose

Without a mental map of the PRG agent system, developers waste time grepping random files, accidentally break routing, or duplicate logic that already exists. The system has three independent agent layers — `AgentExecutor` (trigger matching), `RalphEngine` (autonomous loop), and `AgentWorkflow` (setup/start pipeline) — each with different responsibilities that are easy to confuse.

## Auto-Trigger

Activate when the user asks about:

- **"how does prg agent work"** / **"how does auto-trigger matching work"**
- **"add a trigger"** / **"trigger not matching"** / **"wrong skill matched"**
- **"how does ralph work"** / **"ralph loop"** / **"ralph iteration"**
- **"add a new command"** / **"extend the agent"**
- **"synonym expansion"** / **"fallback triggers"**

## Architecture Map

```
prg agent "fix the bug"
    │
    └─► AgentExecutor.match_skill()          cli/agent.py → generator/planning/agent_executor.py
            │
            ├─ Pass 1: auto-triggers.json     .clinerules/auto-triggers.json  (project-specific)
            └─ Pass 2: _BUILTIN_FALLBACK_TRIGGERS (hardcoded in agent_executor.py)

prg start / prg setup
    │
    └─► AgentWorkflow                         generator/planning/workflow.py
            │
            ├─ TaskCreator  (task_creator.py)
            ├─ Preflight    (preflight.py)
            └─ TaskExecutor (task_executor.py)

prg ralph run FEATURE-001
    │
    └─► RalphEngine.run_loop()               generator/ralph/engine.py
            iteration:
            1. _step_context()   — build context (rules.md + PLAN.md + git log)
            2. _step_skill()     — AgentExecutor.match_skill(context)
            3. _step_agent()     — TaskImplementationAgent.implement()
            4. _step_commit()    — git add + git commit
            5. _step_review()    — SelfReviewer.review(PLAN.md)
            6. _step_tests()     — pytest / jest auto-detected
```

## Process

### 1. Identify Which Layer Is Involved

Before reading code, map the user's question to one of the three layers.

```bash
# Which command is the user's entry point?
grep -n "def agent_command\|def start\|def setup\|def ralph" cli/agent.py cli/ralph_cmd.py
```

| Command | Layer | Key module |
|---|---|---|
| `prg agent <query>` | Trigger matching | `generator/planning/agent_executor.py` |
| `prg start / prg setup` | Workflow pipeline | `generator/planning/workflow.py` |
| `prg ralph run` | Autonomous loop | `generator/ralph/engine.py` |

### 2. Debug Trigger Matching Issues

Why: `AgentExecutor` uses a two-pass strategy — project file first, builtin fallback second. A miss usually means the phrase isn't in either source.

```bash
# Step 1: Check what's in the project's auto-triggers.json
cat .clinerules/auto-triggers.json | python -m json.tool

# Step 2: Check what phrases are in the builtin fallback table
grep -A 5 "_BUILTIN_FALLBACK_TRIGGERS" generator/planning/agent_executor.py

# Step 3: Check what synonym expansion does to the input
python - <<'PY'
from generator.planning.agent_executor import _expand_input
print(_expand_input("the tests are broken"))
PY

# Step 4: Run the full matching trace with debug logging
python - <<'PY'
import logging, pathlib
logging.basicConfig(level=logging.DEBUG)
from generator.planning.agent_executor import AgentExecutor
exe = AgentExecutor(pathlib.Path("."))
print(exe.match_skill("the tests are broken"))
PY
```

**Add a trigger phrase** — two places to update:

1. **Project-specific** (regenerated on `prg analyze`): add a `When …` line to the skill's `description` frontmatter
2. **Builtin fallback** (hardcoded): edit `_BUILTIN_FALLBACK_TRIGGERS` in `generator/planning/agent_executor.py`
3. **Synonym expansion** (catch natural language variants): add a regex tuple to `_SYNONYM_PATTERNS` in the same file

### 3. Inspect or Modify the Ralph Loop

Why: RalphEngine's loop is a 6-step pipeline. Exit conditions and score thresholds are constants at the top of `generator/ralph/engine.py` — misunderstanding them leads to loops that stop too early or never stop.

```bash
# View the numeric thresholds
grep "REVIEW_SCORE\|CONSECUTIVE_FAILURE\|TIMEOUT" generator/ralph/engine.py | head -12

# Inspect current state of a running feature
cat features/FEATURE-001/STATE.json | python -m json.tool

# Check critiques from past iterations
ls features/FEATURE-001/CRITIQUES/
cat features/FEATURE-001/CRITIQUES/iter-001.md
```

**Key thresholds** (constants in `engine.py`):

| Constant | Default | Meaning |
|---|---|---|
| `REVIEW_SCORE_EMERGENCY_STOP` | 60 | Loop halts immediately, human required |
| `REVIEW_SCORE_TASK_COMPLETE` | 70 | Task is marked done |
| `REVIEW_SCORE_SUCCESS_GATE` | 85 | Feature is considered complete |
| `CONSECUTIVE_FAILURE_LIMIT` | 3 | Agent or test failures before stopping |

### 4. Validate Changes Don't Break Routing

Why: trigger matching has unit tests; breaking it silently is the most common regression when editing `agent_executor.py`.

```bash
# Run only the agent routing tests
pytest tests/test_agent_executor.py tests/test_agent_command.py -v

# Validate the full suite still passes
pytest --tb=short -q
```

### 5. Add a New CLI Command

Why: all commands follow the same registration pattern; skipping any step means the command is silently missing.

1. Create `cli/cmd_<name>.py` with a `@click.command(name="<name>")` decorated function.
2. Import it in `cli/cli.py` following the existing block (lines 67–83).
3. Register with `cli.add_command(<name>)` (lines 85–109).
4. Add tests in `tests/test_cmd_<name>.py`.

```bash
# Verify the command appears in the CLI after adding it
python -m cli.cli --help | grep "<name>"
```

## Output

- Clear identification of which layer is involved
- Root cause of trigger mismatch with exact fix location
- Verified changes with passing tests

## Anti-Patterns

❌ **Don't** edit `auto-triggers.json` directly — it is regenerated by `prg analyze` and `prg skills create`. Edit skill frontmatter descriptions or `_BUILTIN_FALLBACK_TRIGGERS` instead.

❌ **Don't** add agent logic to `cli/cli.py` — it is only a registration file. The actual logic belongs in the appropriate `generator/planning/` module.

❌ **Don't** change Ralph thresholds without running the full test suite — `tests/test_ralph_engine.py` verifies every exit condition and score boundary.

❌ **Don't** assume `prg agent` runs code — it is *only* a trigger-matching simulator. Actual execution happens in `prg start` / `prg ralph run`.

# Ralph Feature Loop — Reference

PRG generates structured memory artifacts (rules, skills, plans, specs). Ralph is an optional autonomous execution loop that consumes that memory to implement a specific feature.

---

## Mental Model

```
prg analyze . --incremental     # generate/refresh memory artifacts
prg ralph "Add loading states"  # (optional) autonomous feature loop
prg ralph approve FEATURE-001   # merge when satisfied
```

Ralph is not the default path. Stop after `prg analyze` and work manually whenever you prefer.

---

## Commands

| Command | What it does |
|---------|-------------|
| `prg ralph "task description"` | Create feature workspace + run loop immediately |
| `prg ralph go "task"` | Same as above (explicit form) |
| `prg ralph discover` | Scan README/spec.md, extract features, queue them |
| `prg ralph discover --run` | Discover + execute features sequentially |
| `prg ralph run FEATURE-001` | Start loop for an existing feature |
| `prg ralph status FEATURE-001` | Show iteration progress and STATE.json |
| `prg ralph resume FEATURE-001` | Continue an interrupted loop |
| `prg ralph stop FEATURE-001 --reason "..."` | Emergency stop, saves state |
| `prg ralph approve FEATURE-001` | Merge branch → main, create PR |
| `prg feature "task"` | Create workspace only (no loop) |

Deprecated (redirect to Ralph):
- `prg autopilot` → `prg ralph "task"`
- `prg manager` → `prg ralph discover`

---

## File Structure

```
features/
└── FEATURE-001/
    ├── PLAN.md          # task decomposition
    ├── TASKS.yaml       # pending/done task list
    ├── STATE.json       # loop state (iteration, score, branch)
    └── CRITIQUES/       # per-iteration self-review outputs
```

---

## STATE.json Schema

```json
{
  "feature_id": "FEATURE-001",
  "task": "Add loading states to all forms",
  "branch_name": "ralph/FEATURE-001-add-loading-states",
  "status": "running",
  "iteration": 4,
  "tasks_total": 8,
  "tasks_complete": 3,
  "max_iterations": 20,
  "last_review_score": 82,
  "test_pass_rate": 1.0,
  "exit_condition": null,
  "consecutive_test_failures": 0,
  "human_feedback": null
}
```

---

## Loop Logic (per iteration)

1. **Context** — reads `.clinerules/rules.md` + `PLAN.md` + git log
2. **Skill match** — `AgentExecutor.match_skill()` against auto-triggers
3. **Agent execute** — `TaskImplementationAgent` writes files to disk
4. **Git commit** — `ralph iter N: <task title>`
5. **Self-review** — `SelfReviewer`, score saved to `CRITIQUES/iter-NNN.md`
6. **Tests** — pytest or jest; 3 consecutive failures → stop
7. **Mark task done** — if score ≥ 70 and tests pass

---

## Exit Conditions

| Condition | Status set | Action |
|-----------|-----------|--------|
| All tasks done + score ≥ 85 + tests pass | `success` | Auto-create PR |
| Max iterations reached | `max_iterations` | Create PR with findings |
| Review score < 60 | `stopped` | Emergency stop, notify |
| Tests fail 3× in a row | `stopped` | Stop for human intervention |
| `prg ralph stop` called | `stopped` | Save state, checkout main |

Resume after stop: `prg ralph resume FEATURE-001`

---

## Core Modules

| File | Role |
|------|------|
| `generator/ralph_engine.py` | `RalphEngine`, `FeatureState`, helpers |
| `core/ralph.py` | Re-export shim (canonical import path) |
| `cli/ralph_cmd.py` | CLI commands (go, discover, run, status, resume, stop, approve) |
| `cli/feature_cmd.py` | `prg feature` workspace setup |

---

## Example Run

This is a real smoke test run by Gemini on PRG itself:

```bash
prg ralph "Add loading states to all forms"
```

**What happened:**

```
features/
└── FEATURE-001/
    ├── PLAN.md          # 1 subtask: "Create useLoading Custom Hook"
    ├── TASKS.yaml       # status: pending
    ├── STATE.json       # stopped after iter 6, exit_condition: test_fail_3x
    └── CRITIQUES/
        ├── iter-001.md  # score 70 — "Changes section incomplete"
        └── ...          # iter 002–006: same pattern
```

**Final STATE.json (abbreviated):**

```json
{
  "feature_id": "FEATURE-001",
  "task": "Add loading states to all forms",
  "status": "stopped",
  "iteration": 6,
  "last_review_score": 70,
  "test_pass_rate": 0.0,
  "exit_condition": "test_fail_3x",
  "consecutive_test_failures": 3
}
```

**What to do after a `test_fail_3x` stop:**

The loop stopped because the target project had no test runner configured (PRG is a Python CLI; the task was a React hook). This is expected when running Ralph on a project without tests for that tech stack.

Options:
- `prg ralph resume FEATURE-001` — continue after fixing the root cause manually
- `prg ralph approve FEATURE-001` — merge as-is if you're satisfied with the output
- `prg ralph stop FEATURE-001 --reason "wrong project"` — discard cleanly

> `features/` is excluded from git (`.gitignore`). Each Ralph workspace is local by default.

---

## What PRG Does Not Touch (during Ralph)

- `.clinerules/` generation
- `prg analyze --incremental`
- `prg skills` / `prg review`
- Skill tracking
- `prg watch`

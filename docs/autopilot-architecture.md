# Autopilot Architecture (v1.1)

## Overview

The autopilot system is a supervised execution loop that takes a task manifest
(TASKS.yaml), implements each task via an AI agent, runs tests, and asks the user
to approve/skip/stop — with full git branch isolation per task.

## Core Components

| File | Role |
|------|------|
| `generator/planning/autopilot.py` | **AutopilotOrchestrator** — discovery + supervised execution loop |
| `generator/planning/workflow.py` | **AgentWorkflow** — project setup (rules, skills, plan, tasks) |
| `generator/planning/task_creator.py` | **TaskManifest** — loads and parses TASKS.yaml |
| `generator/planning/task_executor.py` | **TaskExecutor** — tracks task state (pending/executing/done) |
| `generator/planning/task_agent.py` | **TaskImplementationAgent** — calls LLM to produce file changes |
| `generator/planning/project_manager.py` | **ProjectManager** — 4-phase lifecycle orchestrator |
| `prg_utils/git_ops.py` | **git_ops** — branch create/merge/delete/rollback |

## Two Entry Points

```
prg autopilot <task>                   prg manager
      │                                      │
      ▼                                      ▼
AutopilotOrchestrator                  ProjectManager
      │                                      │
      ├── discovery(task_description)        ├── phase1_setup()
      │       └── AgentWorkflow.run_setup()  │       ├── generate missing docs
      │                                      │       │   (rules, skills, PLAN.md,
      └── execution_loop(manifest)           │       │    spec.md, ARCHITECTURE.md,
                                             │       │    tests/, pytest.ini)
                                             │       └── _update_manager_checklist()
                                             │
                                             ├── phase2_verify()   [PreflightChecker]
                                             ├── phase3_copilot()  [execution_loop]
                                             └── phase4_summary()  [PROJECT-COMPLETION.md]
```

## Discovery Phase

```
AutopilotOrchestrator.discovery(task_description)
        │
        ▼
AgentWorkflow.run_setup()
        │
        ├── Analyze project  (tech_stack, README, structure)
        ├── Generate rules   → .clinerules/rules.md       [CoworkRulesCreator]
        ├── Generate skills  → .clinerules/skills/        [SkillGenerator]
        ├── Generate plan    → PLAN.md                    [ProjectPlanner / LLM]
        └── Generate tasks   → tasks/TASKS.yaml           [TaskCreator]
                                     │
                                     ▼
                              TaskManifest (list of TaskEntry)
```

## Execution Loop (v1.1)

```
execution_loop(manifest)
        │
        ▼
TaskExecutor.get_next_task()  ──── None? ──── _print_summary() ──── END
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Per-Task Flow                                                    │
│                                                                   │
│  ① git branch create  →  "autopilot/task-{id}"                   │
│          │                                                        │
│  ② TaskImplementationAgent.implement(subtask, project_context)   │
│          │                                                        │
│          │  LLM generates file changes: { path: content }        │
│          │  Files written to project_path/                       │
│          │                                                        │
│  ③ _run_tests(subtask)                                            │
│          │                                                        │
│          ├── _detect_test_runner()                                │
│          │        ├── pytest.ini / pyproject.toml / conftest.py  │
│          │        │       → pytest -x -q [test_files]            │
│          │        ├── package.json                                │
│          │        │       → npx jest --passWithNoTests --bail     │
│          │        └── none → skip (return True, "No runner")     │
│          │                                                        │
│          └── subprocess.run(timeout=120s) → (passed, output)     │
│                                                                   │
│  ④ _print_test_results(passed, output)                            │
│          └── last 15 lines of output                             │
│                                                                   │
│  ⑤ _ask_user(title, goal, tests_passed)                           │
│          │                                                        │
│          │  [a] Approve & merge                                   │
│          │  [s] Skip this task                                    │
│          │  [q] Stop autopilot                                    │
│          │                                                        │
│          │  ⚠️  If tests failed → warning shown before prompt     │
│          │                                                        │
└──────────┼────────────────────────────────────────────────────────┘
           │
     ┌─────┼──────────────────────────────────┐
     │     │                                  │
   APPROVE SKIP                             STOP
     │     │                                  │
     ▼     ▼                                  ▼
  merge  checkout main               checkout main
  branch delete branch               delete branch
  completed += 1  skipped += 1       rollback_to_head()
     │     │                         _print_summary()
     └─────┘                                  │
        │                                   BREAK
        ▼
  get_next_task()  ──── loop ────►
```

## Git Safety Model

```
main branch
    │
    ├── autopilot/task-1  ←── agent writes files here
    │        │
    │        │  [approve]  →  merge into main, delete branch
    │        │  [skip]     →  checkout main, delete branch (changes discarded)
    │        │  [stop]     →  checkout main, delete branch, rollback_to_head()
    │        │  [error]    →  checkout main, rollback_to_head()
    │
    ├── autopilot/task-2  ←── next iteration
    │        │
    │       ...
    │
    └── main (clean after every decision)
```

## spec.md Generation (Phase 1, ProjectManager)

When `spec.md` is missing, `ProjectManager._generate_spec_md()` generates it via LLM:

```
_generate_spec_md()
        │
        ├── README.md (up to 2500 chars)
        ├── PLAN.md excerpt (up to 1500 chars, if exists)
        ├── git log --oneline -20
        └── build_project_tree()   [readme_bridge.py]
                │
                ▼
        LLM prompt → structured spec.md:

        # Project Specification
        ## Overview
        ## Goals             (3-5 measurable outcomes)
        ## User Personas     (2-3 personas with needs)
        ## User Stories      (5-8, As a / I want / so that)
        ## Constraints       (technical + non-functional)
        ## Acceptance Criteria   (Given/when/then, numbered)
        ## Out of Scope
```

## Summary Output

```
_print_summary(completed, skipped)

  ════════════════════════════════════════════════
  🎉 Autopilot run complete
     ✅ Completed : 4
     ⏭️  Skipped   : 1
  ════════════════════════════════════════════════
```

## Error Handling

| Scenario | Behavior |
|---|---|
| `git` not available | Safety features disabled, loop continues |
| Branch creation fails | Warning printed, task proceeds without branch |
| Agent `implement()` throws | Checkout main + rollback_to_head() + break |
| Tests timeout (> 120s) | `passed=False`, shows "timed out" message |
| Test runner not found | `passed=True`, shows "skipping" — non-blocking |
| LLM generate fails | Exception propagates up to task error handler |

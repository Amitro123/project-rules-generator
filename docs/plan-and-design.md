# PRG — Feature Plan & Design Document

> Based on `docs/features.md` cross-referenced with `PROJECT-ROADMAP.md`, `PRG_WOW_PLAN.md`, and the current codebase state.
> Generated: 2026-03-25

---

## 1. Current State Snapshot

| Feature | Documented In features.md | Implementation Status |
|---|---|---|
| Basic Analysis (`prg analyze .`) | ✅ | ✅ Fully working |
| AI Skills (`--ai --provider`) | ✅ | ✅ Fully working (4 providers) |
| Incremental Mode (`--incremental`) | ✅ | ✅ Implemented (`IncrementalAnalyzer`) |
| Task Breakdown (`prg plan`) | ✅ | ⚠️ Exists, not battle-tested |
| Two-Stage Planning (`prg design` + `prg plan --from-design`) | ✅ | ⚠️ Exists, not battle-tested |
| Constitution (`--constitution`) | ✅ | ✅ Fully working |
| Skill Management (`--add/remove/list-skills`) | ✅ | ✅ Fully working |
| Smart Skill Orchestration (`prg agent`) | ✅ | ✅ `TriggerEvaluator` + 3-layer resolution |
| Autopilot (`prg autopilot .`) | ✅ | ⚠️ `AutopilotOrchestrator` exists, untested |
| Project Manager (`prg manager .`) | ✅ | ⚠️ Exists, untested |
| **Evolution / feedback loop** | Referenced in roadmap | ❌ Not implemented |
| **`prg skills` sub-commands** | PRG_WOW_PLAN only | ❌ Not implemented |
| **`prg init` wizard** | PRG_WOW_PLAN only | ❌ Not implemented |
| **Rich CLI output** | PRG_WOW_PLAN only | ❌ Not implemented (`rich` in deps, unused) |

---

## 2. Gap Analysis

### 2.1 Content gaps (features documented but broken/untested)

**Autopilot** — `AutopilotOrchestrator` exists in `generator/autopilot/` but has no test coverage and is not wired to a stable `prg autopilot` command. The git-branch-per-task and human-review loop described in `features.md` are not verified end-to-end.

**Two-Stage Planning** — `prg design` and `prg plan --from-design` exist as CLI commands but the design → plan handoff (reading `DESIGN.md` and generating a dependency-aware `PLAN.md`) is untested against real projects.

**Task Breakdown** — `prg plan "task description"` exists but AI decomposition quality is not validated; no tests cover the `PLAN.md` output format.

### 2.2 Missing features (in roadmap, not in codebase)

**Evolution loop** — Skills are stored in `~/.project-rules-generator/learned/` but never updated based on usage. No quality-score feedback, no promotion/demotion logic.

**`prg skills` sub-commands** — `TriggerEvaluator` precision scoring is internal only; no `prg skills list/validate/import` commands exist.

**`prg init` wizard** — No interactive first-run experience. Users must know the exact CLI flags to get value.

**Rich CLI output** — `rich` is declared in `requirements.txt` but every command uses plain `print()` / `click.echo()`.

---

## 3. Proposed Work — Prioritised

### Priority 1 — Stabilise existing features (short-term, high confidence)

These features are documented and partially built. They just need test coverage and validation.

#### P1-A: Autopilot end-to-end test

**Goal:** Verify the `prg autopilot .` loop against a controlled fixture project.

**Files:** `generator/autopilot/orchestrator.py`, new `tests/test_autopilot_flow.py`

**Design:**
```
AutopilotOrchestrator
  ├── analyze()         → reads project context
  ├── plan()            → writes TASKS.yaml + PLAN.md
  ├── execute_next()    → picks next pending task, creates git branch
  ├── verify()          → runs pytest / ruff
  └── review_prompt()   → returns diff + asks human yes/no
```

**Test approach:** Use a temp git repo fixture with two pre-defined failing tests. Verify the orchestrator creates a branch, makes changes, and prompts for review without crashing.

**Acceptance:** `pytest tests/test_autopilot_flow.py` passes; `prg autopilot .` runs on the sample project without raising an unhandled exception.

---

#### P1-B: Two-Stage Planning validation

**Goal:** Verify `prg design "X"` + `prg plan --from-design DESIGN.md` produce coherent, non-empty output.

**Files:** `generator/planning/design_generator.py`, `generator/planning/project_manager.py`, new `tests/test_two_stage_planning.py`

**Design:**
```
Stage 1:  prg design "Add auth"
          └── DesignGenerator.generate(feature_description)
              ├── Produces DESIGN.md with:
              │   - Architecture Decisions
              │   - Data Models
              │   └── API Contracts
              └── Saved to project root

Stage 2:  prg plan --from-design DESIGN.md
          └── ProjectPlanner.plan_from_design(design_path)
              ├── Reads DESIGN.md
              ├── Decomposes each API Contract into tasks
              └── Writes PLAN.md with estimated times + dependencies
```

**Gap to fix:** `ProjectPlanner` currently does not read `DESIGN.md` as a structured input — it re-runs analysis from scratch. The `--from-design` flag needs to inject the design document as primary context, not as a supplementary hint.

---

#### P1-C: Task Breakdown output validation

**Goal:** Ensure `prg plan "task"` always produces a `PLAN.md` with at least 2 tasks in the correct format.

**Files:** `generator/planning/task_breakdown.py`, `tests/test_task_breakdown.py`

**Acceptance criteria (from features.md format):**
```
- Each task block has: Goal, Files, Dependencies, Estimated time
- At least one task has a "Tests" section
- Tasks are numbered and dependency-ordered
```

---

### Priority 2 — Evolution loop (medium-term, architecture design needed)

**Goal:** Skills improve based on usage — the "gets smarter" promise from features.md.

#### Design

```
┌─────────────────────────────────────────────────────────┐
│                  Evolution Engine                        │
│                                                         │
│  UsageTracker          QualityFeedback                  │
│  ─────────────         ───────────────                  │
│  .track(skill, event)  .record(skill, score, context)   │
│                                                         │
│  EvolutionScheduler                                     │
│  ──────────────────                                     │
│  .should_evolve(skill) → bool   (usage threshold)       │
│  .evolve(skill)        → new SKILL.md                   │
│         │                                               │
│         └── re-runs AIStrategy with:                    │
│             - current SKILL.md as base                  │
│             - quality_report from last N runs           │
│             - recent trigger hits/misses                │
└─────────────────────────────────────────────────────────┘
```

**Storage schema** (append to `~/.project-rules-generator/usage.jsonl`):
```json
{"skill": "pytest-testing-workflow", "event": "triggered", "score": 95, "ts": "2026-03-25T10:00:00"}
{"skill": "pytest-testing-workflow", "event": "dismissed", "score": null, "ts": "2026-03-25T10:01:00"}
```

**Evolution trigger:** After 10 uses OR quality score drops below 70 on 3 consecutive runs, `EvolutionScheduler` re-generates the skill using `AIStrategy` seeded with the current content and feedback history.

**Files to create:**
- `generator/evolution/usage_tracker.py`
- `generator/evolution/quality_feedback.py`
- `generator/evolution/evolution_scheduler.py`
- `generator/evolution/__init__.py`

**Integration point:** `SkillsManager.create_skill()` — after writing a skill, call `UsageTracker.track(skill_name, "created")`. After `prg agent` matches a skill, track `"triggered"`.

---

### Priority 3 — `prg skills` sub-commands (medium-term, high visibility)

**Goal:** Surface the hidden `TriggerEvaluator` power as user-facing commands.

#### 3.1 `prg skills list`

```bash
prg skills list

┌──────────────────────────────┬──────────┬─────────┬───────┐
│ Name                         │ Layer    │Triggers │ Score │
├──────────────────────────────┼──────────┼─────────┼───────┤
│ pytest-testing-workflow      │ learned  │ 1       │ 90    │
│ systematic-debugging         │ builtin  │ 3       │ 100   │
│ test-driven-development      │ builtin  │ 4       │ 100   │
└──────────────────────────────┴──────────┴─────────┴───────┘
```

**File:** new `cli/skills_cmd.py` — `@cli.group("skills")` with `list`, `validate`, `import` sub-commands.

#### 3.2 `prg skills validate <name>`

Runs `TriggerEvaluator` and prints precision/recall breakdown for a named skill.

#### 3.3 `prg skills import <url>`

Fetches a raw SKILL.md from a GitHub URL and saves it to `learned/` after running `validate_quality()`. Rejects if score < 90.

---

### Priority 4 — `prg init` wizard + Rich CLI (long-term, first impression)

#### 4.1 `prg init`

Interactive first-run wizard:
1. Detects available API keys from environment.
2. Asks which provider to use (with speed/cost guidance).
3. Runs `prg analyze .` with the selected provider.
4. Prints a "You're ready" summary with next steps.

**File:** `cli/init_cmd.py`

#### 4.2 Rich CLI output

Wire `rich` to the three main commands:

| Command | Rich component |
|---|---|
| `prg analyze .` | `Progress` spinner per step + `Table` for rule summary |
| `prg create-rules .` | `Panel` with live rule count + `Console.rule()` section dividers |
| `prg skills list` | `Table` (see above) |
| Error messages | `Console.print("[red]Error:[/]")` with provider-specific hints |

No new dependencies — `rich` is already in `requirements.txt`.

---

## 4. Implementation Order

```
P1-A  Autopilot tests           → low-risk, no architecture change
P1-B  Two-stage planning fix    → fix --from-design input path
P1-C  Task breakdown validation → add output format tests
  ↓
P2    Evolution loop             → new generator/evolution/ module
  ↓
P3    prg skills sub-commands   → new cli/skills_cmd.py
  ↓
P4    prg init + Rich            → surface polish, no new logic
```

Each step is independently releasable and adds tests before shipping.

---

## 5. Files Touched Per Phase

| Phase | New files | Modified files |
|---|---|---|
| P1-A | `tests/test_autopilot_e2e.py` | `generator/autopilot/orchestrator.py` (bug fixes) |
| P1-B | `tests/test_two_stage_planning.py` | `generator/planning/project_manager.py`, `cli/analyze_cmd.py` |
| P1-C | `tests/test_task_breakdown_format.py` | `generator/planning/task_breakdown.py` |
| P2 | `generator/evolution/` (4 files) | `generator/skills_manager.py`, `cli/analyze_cmd.py` |
| P3 | `cli/skills_cmd.py`, `tests/test_skills_cmd.py` | `cli/cli.py` (register group) |
| P4 | `cli/init_cmd.py` | `cli/analyze_cmd.py`, `cli/create_rules_cmd.py` |

---

## 6. Open Questions

1. **Evolution re-generation** — should it silently overwrite the skill or write a `skill-v2.md` for human review first? Recommend: write to a `.draft` file + prompt user on next `prg analyze`.

2. **`prg skills import` trust model** — should imported skills go straight to `learned/` or to a `pending/` quarantine until `prg agent` uses them once successfully?

3. **Autopilot human-in-the-loop UX** — `features.md` says "Asks for your approval". Should this be a blocking CLI prompt or a PR draft on GitHub? For v1, blocking CLI is simpler and testable.

4. **Two-Stage Planning storage** — `DESIGN.md` and `PLAN.md` go in the project root today. For multi-feature work, a `plans/` directory with dated filenames (`plans/2026-03-25-auth.md`) would be cleaner.

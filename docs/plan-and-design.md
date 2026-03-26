# PRG — Feature Plan & Design Document

> Based on `docs/features.md` cross-referenced with `PROJECT-ROADMAP.md`, `PRG_WOW_PLAN.md`, and the current codebase state.
> Updated: 2026-03-26

---

## 1. Current State Snapshot

| Feature | Documented In features.md | Implementation Status |
|---|---|---|
| Basic Analysis (`prg analyze .`) | ✅ | ✅ Fully working |
| AI Skills (`--ai --provider`) | ✅ | ✅ Fully working (4 providers) |
| Incremental Mode (`--incremental`) | ✅ | ✅ Implemented (`IncrementalAnalyzer`) |
| Task Breakdown (`prg plan`) | ✅ | ✅ Implemented + tested (`test_task_decomposer.py`, `test_plan_modes.py`) |
| Two-Stage Planning (`prg design` + `prg plan --from-design`) | ✅ | ✅ Implemented + tested (`test_two_stage_planning.py` — 9 tests passing) |
| Constitution (`--constitution`) | ✅ | ✅ Fully working |
| Skill Management (`--add/remove/list-skills`) | ✅ | ✅ Fully working |
| Smart Skill Orchestration (`prg agent`) | ✅ | ✅ `TriggerEvaluator` + 3-layer resolution |
| Autopilot (`prg autopilot .`) | ✅ | ✅ `AutopilotOrchestrator` implemented + tested (`test_autopilot_flow.py` — 9 tests passing) |
| Project Manager (`prg manager .`) | ✅ | ⚠️ Exists, not deeply battle-tested |
| `analyze_cmd.py` modularisation | Internal concern | 🔄 In progress (1100+ lines, split underway) |
| **Evolution / feedback loop** | Referenced in roadmap | ❌ Not implemented |
| **`prg skills` sub-commands** | PRG_WOW_PLAN only | ❌ Not implemented |
| **`prg init` wizard** | PRG_WOW_PLAN only | ❌ Not implemented |
| **Rich CLI output** | PRG_WOW_PLAN only | ❌ Not implemented (`rich` in deps, unused) |

---

## 2. Gap Analysis

### 2.1 Resolved gaps (updated 2026-03-26)

**Autopilot** — `AutopilotOrchestrator` is fully implemented in `generator/planning/autopilot.py` and covered by `tests/test_autopilot_flow.py` (3 scenarios: discovery, happy-path execution loop, rejection+rollback). All 9 autopilot tests pass.

**Two-Stage Planning** — `prg design` + `prg plan --from-design` are wired end-to-end. `TaskDecomposer.from_design()` now reads the DESIGN.md as primary context (not a supplementary hint). Covered by `tests/test_two_stage_planning.py` (6 scenarios). All tests pass.

**Task Breakdown** — `prg plan "task description"` is covered in `tests/test_task_decomposer.py` and `tests/test_plan_modes.py`. Output format validated (Goal / Files / Dependencies / Estimated time structure).

### 2.2 Remaining gaps (features in roadmap, not in codebase)

**Evolution loop** — Skills are stored in `~/.project-rules-generator/learned/` but never updated based on usage. No quality-score feedback, no promotion/demotion logic, no `generator/evolution/` module.

**`prg skills` sub-commands** — `TriggerEvaluator` precision scoring is internal only; no `prg skills list/validate/import` commands exist. No `cli/skills_cmd.py`.

**`prg init` wizard** — No interactive first-run experience. Users must know the exact CLI flags to get value. No `cli/init_cmd.py`.

**Rich CLI output** — `rich` is declared in `requirements.txt` but every command uses plain `print()` / `click.echo()`.

**`analyze_cmd.py` split** — File is 1100+ lines. Modularisation is in progress but not complete.

---

## 3. Proposed Work — Prioritised

### Priority 1 — `analyze_cmd.py` modularisation (in-progress, low risk)

**Goal:** Break the 1100-line monolith into focused sub-modules without changing public API.

**Proposed split:**
```
cli/analyze_cmd.py  (router only — imports + Click decorators)
cli/analyze/
  ├── ai_flow.py       # --ai branch: provider routing + skill generation
  ├── readme_flow.py   # --from-readme branch
  ├── incremental.py   # --incremental branch
  └── output.py        # shared output/commit helpers
```

**Acceptance:** All existing tests pass. `prg analyze .` behaviour unchanged. Each sub-module ≤ 200 lines.

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
{"skill": "pytest-testing-workflow", "event": "triggered", "score": 95, "ts": "2026-03-26T10:00:00"}
{"skill": "pytest-testing-workflow", "event": "dismissed", "score": null, "ts": "2026-03-26T10:01:00"}
```

**Evolution trigger:** After 10 uses OR quality score drops below 70 on 3 consecutive runs, `EvolutionScheduler` re-generates the skill using `AIStrategy` seeded with the current content and feedback history.

**Resolved design question:** Evolution writes to a `.draft` file first (e.g., `pytest-testing-workflow.draft.md`) and prompts the user on next `prg analyze` — it does NOT silently overwrite. (See section 6.1.)

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

**Resolved design question:** Imported skills go to `pending/` quarantine first. After `prg agent` uses them once successfully (triggered + not dismissed), they are promoted to `learned/`. (See section 6.2.)

Fetches a raw SKILL.md from a GitHub URL and saves it to `pending/` after running `validate_quality()`. Rejects if score < 90.

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

**Resolved design question:** Autopilot human-in-the-loop UX uses a blocking CLI prompt for v1 (simpler and testable). GitHub PR drafts deferred to a future version. (See section 6.3.)

---

## 4. Implementation Order

```
P1    analyze_cmd.py split      → low-risk, internal refactor, no behaviour change
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
| P1 | `cli/analyze/ai_flow.py`, `cli/analyze/readme_flow.py`, `cli/analyze/incremental.py`, `cli/analyze/output.py` | `cli/analyze_cmd.py` (gutted to router) |
| P2 | `generator/evolution/` (4 files), `tests/test_evolution.py` | `generator/skills_manager.py`, `cli/analyze_cmd.py` |
| P3 | `cli/skills_cmd.py`, `tests/test_skills_cmd.py` | `cli/cli.py` (register group) |
| P4 | `cli/init_cmd.py` | `cli/analyze_cmd.py`, `cli/create_rules_cmd.py` |

---

## 6. Resolved Design Questions

> Previously open questions — answers locked in here for reference.

**6.1 Evolution re-generation** — Resolved: write to a `.draft` file (e.g., `pytest-testing-workflow.draft.md`) + prompt user on next `prg analyze`. Never silently overwrite.

**6.2 `prg skills import` trust model** — Resolved: Imported skills go to `pending/` quarantine first. They are promoted to `learned/` only after one successful use by `prg agent` (triggered + not dismissed by the user).

**6.3 Autopilot human-in-the-loop UX** — Resolved: blocking CLI prompt for v1. `features.md` says "Asks for your approval" — implemented as `click.prompt()`. GitHub PR draft deferred to a future version when the user base is larger.

**6.4 Two-Stage Planning storage** — Deferred: `DESIGN.md` and `PLAN.md` stay in the project root for now. Multi-feature `plans/` directory with dated filenames is noted for a future cleanup pass.

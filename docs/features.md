# Features Overview

Project Rules Generator offers a suite of tools to analyze your codebase and generate context-aware rules for AI agents.

## Feature Breakdown

| Feature | Description | Speed | AI Required | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Basic Analysis** | Scans code structure & README for rules | Fast | No | ✅ |
| **AI Skills** | Uses LLM to generate custom skills | Slow | Yes | ✅ |
| **Incremental** | Updates only changed sections | Very Fast | No | ✅ |
| **Task Breakdown** | Breaks large tasks into smaller steps | Medium | Yes | ✅ |
| **Autopilot** | End-to-end discovery & execution loop (supervised) | Slow | Yes | ✅ |
| **Project Manager** | Lifecycle orchestration (Setup→Verify→Exec→Report) | Slow | Yes | ✅ |
| **Two-Stage Planning** | Design → Plan workflow for complex features | Slow | Yes | ✅ |
| **Constitution** | Generates high-level principles | Fast | No | ✅ |
| **Skill Management** (`--create-skill`, `--list-skills`) | Managing your learned/project skills library | Instant | No | ✅ |
| **`prg init`** | First-run wizard — detect stack, generate rules, print next steps | Fast | No | ✅ |
| **`prg skills list/validate/show`** | Sub-commands for skill inspection and validation | Instant | No | ✅ |
| **`prg watch`** | Watches project files and auto-runs `analyze --incremental` on change | Instant | No | ✅ |
| **Spec Generation** | LLM-generated `spec.md` (Overview, Goals, User Stories, Acceptance Criteria) | Medium | Yes | ✅ |
| **Skill Usage Tracking** | Auto-tracks match counts; `feedback` votes; `stale` detection | Instant | No | ✅ |
| **Ralph Feature Loop** 🔁 | Autonomous feature-scoped iteration loop with git commits & self-review gate | Slow | Yes | ✅ |

---

## Detailed Feature Guide

### Feature 1: Basic Analysis
**What it does**: Analyzes your project and generates coding rules based on actual patterns found in your codebase.

**Command**:
```bash
prg analyze .
```

**Output**:
```
.clinerules/
├── rules.md           # DO/DON'T, testing, dependencies
└── clinerules.yaml    # Lightweight skill references
```

**Use Case**: First-time setup to understand your project conventions without sending code to an LLM.

### Feature 2: AI-Powered Skill Matching
**What it does**: Uses AI to deeply analyze your project architecture and auto-detect which workflow skills would fit best (e.g., TDD, Code Review, Security Auditing).

**Command**:
```bash
prg analyze . --ai
prg analyze . --ai --provider anthropic   # force a specific provider
```

**Output**:
```
.clinerules/
├── rules.md
├── clinerules.yaml
└── skills/
    ├── builtin/
    │   ├── test-driven-development.md
    │   ├── requesting-code-review.md
    │   └── systematic-debugging.md
    ├── learned/            # Project-specific patterns
    └── index.md            # Skills catalog
```

**Use Case**: Create a comprehensive AI assistant that knows specifically how *your* team works.
**Providers**: 
- **Groq** (Default): Free tier, extremely fast (Llama 3.1 8b).
- **Gemini**: Free tier available, high capacity (Gemini 2.0 Flash).
- **Claude**: Paid, high quality.

| Provider | Model | Speed | Cost |
| :--- | :--- | :--- | :--- |
| **Groq** | Llama 3.1 8b | ⚡⚡⚡ | Free |
| **Gemini** | Gemini 2.0 Flash | ⚡⚡ | Free |
| **Claude** | Sonnet 4.6 | ⚡ | Paid |

### Feature 3: Incremental Mode ⚡ NEW
**What it does**: Only regenerates sections rules that have changed since the last run (3-5x faster on large projects).

**Command**:
```bash
prg analyze . --incremental
```

**How it works**:
1. Hashes project state (files, dependencies, tests).
2. Compares with `.clinerules/.prg-cache.json`.
3. Regenerates only changed sections.
4. Merges with existing rules.

**Output**:
```
Changes detected: dependencies, tests
✓ Updated DEPENDENCIES section
✓ Updated TESTING section
⏭ Skipped ARCHITECTURE (unchanged)
```

**Use Case**: Daily updates, CI/CD pipelines, large codebases where full re-analysis is slow.

### Feature 4: Task Breakdown 🎯 NEW
**What it does**: Uses AI to break down large, ambiguous tasks into small, executable subtasks (2-5 minutes each).

**Command**:
```bash
prg plan "Add authentication to API"
```

**Output (PLAN.md)**:
```markdown
## Task 1: Add User model
**Goal**: Create database model for users
**Files**: models/user.py
**Dependencies**: None
**Estimated time**: 3min

### Changes
- Create User class with fields: id, email, password_hash
- Add to models/__init__.py

### Tests
- pytest tests/test_user_model.py -v

## Task 2: Create login endpoint
**Dependencies**: Task 1
...
```

**Use Case**: Break down features before implementation, feed to Subagent-Driven Development skill, or for better estimation & planning.

### Feature 5: Two-Stage Planning 🏗️ NEW
**What it does**: A powerful workflow for complex features. First, generating an architectural design (`DESIGN.md`), then decomposing it into a detailed implementation plan (`PLAN.md`).

**Stage 1: Design**
Generate an architectural decision record with data models and API contracts.
```bash
prg design "Add authentication system"
```
**Output (`DESIGN.md`)**:
- Architecture Decisions (Auth method, storage, etc.)
- Data Models (User, Token)
- API Contracts (POST /login, etc.)

**Stage 2: Plan**
Convert the design into a step-by-step implementation plan.
```bash
prg plan --from-design DESIGN.md
```
**Output (`PLAN.md`)**:
- Detailed tasks mapped to architectural decisions
- Verification steps for each component

**Use Case**: large features requiring architectural thought before coding.

### Feature 6: Constitution Mode
**What it does**: Generates a high-level coding principles document based on your project type.

**Command**:
```bash
prg analyze . --constitution
```

**Output (.clinerules/constitution.md)**:
```markdown
# Constitution

## Code Quality Principles
- Run `pytest` before committing
- Use type hints on all public APIs

## Architecture Decisions
- Project type: python-cli
- Entry points: main.py

## Testing Standards
- Framework: pytest (32 files, 222 tests)
```

**Use Case**: Creating onboarding documentation or a team standards reference.

### Feature 7: Skill Management
**What it does**: Add, remove, or list workflow skills for your project.

**Commands**:
```bash
# List all available skills
prg skills list
prg skills list --all        # include builtin skills

# View a skill's content
prg skills show fastapi-endpoints

# Validate quality score
prg skills validate my-skill

# Create a new skill
prg analyze . --create-skill "auth-flow" --ai
prg analyze . --create-skill "deploy-checklist" --scope project
```

**Output**:
```
Available skills:
  - test-driven-development (builtin)
  - systematic-debugging (builtin)
  - api-optimization (learned)
```

**Use Case**: Customize exactly which workflows the AI uses for your specific project needs.

### Feature 8: Smart Skill Orchestration 🧠 NEW
**What it does**: A sophisticated system that layers skills (Project > Learned > Builtin) and automatically triggers them based on user intent.

**Layered Architecture**:
1.  **Project-Specific** (`.clinerules/skills/project/`): Highest priority. Custom overrides for this repo.
2.  **Global Learned** (`~/.project-rules-generator/learned/`): Medium priority. Your personal library.
3.  **Builtin** (`~/.project-rules-generator/builtin/`): Lowest priority. Default best practices.

**Auto-Triggers**:
Skills can define activation phrases in an `## Auto-Trigger` section. PRG extracts these to `.clinerules/auto-triggers.json` for instant lookup.

**Command**:
```bash
prg agent "I need to fix a bug"
# Output: 🎯 Auto-trigger: systematic-debugging
```

**Use Case**: Building autonomous agents that know *exactly* which tool to use for a specific request, without hallucinating.

### Feature 9: Autopilot 🤖
**What it does**: A project-wide supervised loop that takes a project from zero to implemented features, asking for human approval at each task boundary.

> **Tip**: For feature-scoped *autonomous* iteration (no per-task prompts, persistent state, self-review gate), see [Feature 15: Ralph Feature Loop](#feature-15-ralph-feature-loop-engine-).

**Command**:
```bash
prg autopilot .
```

**Workflow**:
1.  **Analyze**: Scans project context.
2.  **Plan**: Generates a roadmap (`PLAN.md`) and task manifest (`TASKS.yaml`).
3.  **Execute**:
    -   Picks the next pending task.
    -   Creates a git branch (`autopilot/task-001`).
    -   Uses an AI agent to implement the changes.
    -   Runs verification (tests/lint).
4.  **Human Review**: Asks for your approval at every task.
    -   **Yes**: Merges branch.
    -   **No**: Rolls back changes.

**Use Case**: "Supervised" development for well-defined projects with explicit human sign-off on each change.

### Feature 10: Project Manager Agent 👨‍💼 NEW
**What it does**: Acts as a verified project manager. It ensures your project is set up correctly (Plan, Spec, Architecture), validates readiness, and then manages the execution.

**Command**:
```bash
prg manager .
```

**Phases**:
1.  **Setup**: Checks/generates 9 critical artifacts (`rules.md`, `skills/`, `PLAN.md`, `tasks/`, `spec.md`, `tests/`, `pytest.ini`, `README.md`, `ARCHITECTURE.md`).
2.  **Verify**: Runs `PreflightChecker`.
3.  **Copilot**: Runs `Autopilot` loop.
4.  **Summary**: Generates `PROJECT-COMPLETION.md`.

**Use Case**: When you want a structured, professional workflow that guarantees documentation and process compliance.

---

### Feature 11: Spec Generation 📋

**What it does**: Uses an LLM to generate a structured `spec.md` — a complete project specification document covering Overview, Goals, User Personas, User Stories, Constraints, Acceptance Criteria, and Out of Scope sections.

**Command**:
```bash
# Triggered automatically by prg manager when spec.md is missing
prg manager .

# Or invoke directly via the planning pipeline
prg plan "Add authentication system"   # generates PLAN.md; spec.md auto-generated if absent
```

**Output (`spec.md`)**:
```markdown
# Project Specification

## Overview
One paragraph describing what the project does, who it's for, and the core problem it solves.

## Goals
- Concrete, measurable outcome 1
- Concrete, measurable outcome 2

## User Personas
**Developer** (Backend Engineer) — needs to generate project rules without manual setup.

## User Stories
As a developer, I want rules auto-generated so that every AI session starts with project context.

## Constraints
- Python 3.8+ compatibility required
- Must work offline (no API key required for basic analysis)

## Acceptance Criteria
1. Given a project with README.md, when `prg manager .` runs, then spec.md is generated.

## Out of Scope
- Web UI or dashboard
- Real-time collaboration features
```

**Use Case**: Onboarding new contributors, aligning stakeholders on project scope, or feeding structured requirements into the autopilot/planning pipeline.

---

### Feature 12: Self-Review 🔍

**What it does**: Critiques a generated artifact (PLAN.md, skill file, design doc) for quality issues and hallucinations using an LLM + static analysis pass. Detects fabricated file paths, invented library names, and project-specific inconsistencies by cross-referencing the README.

**Command**:
```bash
prg review PLAN.md
prg review .clinerules/skills/learned/my-skill/SKILL.md --project-path .
prg review DESIGN.md --output CRITIQUE.md --tasks
```

**Options**:
- `--project-path` — project root for README context (default: `.`)
- `--output` / `-o` — where to write the critique (default: `CRITIQUE.md` next to input)
- `--tasks` — also generate an actionable task list from the review findings
- `--provider` — AI provider override

**Output (`CRITIQUE.md`)**:
```markdown
# Review Report

**Verdict**: needs_revision
**Score**: 62/100

## Issues
- Hallucinated import: `from mylib.utils import helper` — not found in README

## Suggestions
- Add concrete example commands to the Process section
```

**Fallback**: When the LLM is unavailable, a static hallucination check still runs — detecting invented `src/` paths and common placeholder patterns.

**Use Case**: Quality-gate generated artifacts before committing them. Especially useful after `prg plan` or `prg design` to catch LLM hallucinations early.

---

### Feature 14: Skill Usage Tracking

**What it does**: Builds a persistent feedback loop around skill quality. Every time `prg agent` matches a skill the match count is incremented silently. Developers vote on individual skills after using them, and `prg skills stale` surfaces skills that are consistently unhelpful so they can be regenerated.

**Data file**: `~/.project-rules-generator/skill-usage.json` — accumulates across all projects and sessions.

**Commands**:
```bash
# Record a vote after using a skill
prg skills feedback pytest-testing-workflow --useful
prg skills feedback pytest-testing-workflow --not-useful

# Find skills that are consistently unhelpful
prg skills stale
prg skills stale --threshold 0.5   # stricter cutoff
```

**Example feedback output**:
```
Recorded: 'pytest-testing-workflow' marked as useful. Score: 75% (3 useful / 1 not useful / 8 matches)
```

**Example stale output**:
```
Low-scoring skills (score < 30%, >= 3 votes):
  legacy-deploy-flow   score=20%  useful=1  not_useful=4  matches=12
  old-lint-workflow    score=25%  useful=1  not_useful=3  matches=7

Suggestion: prg analyze . --create-skill <name>  to regenerate each skill.
```

**End-to-end workflow**:
1. `prg agent "fix the failing tests"` — skill matched, `match_count` incremented automatically
2. After working with the skill: `prg skills feedback pytest-testing-workflow --useful`
3. Periodically: `prg skills stale` to find candidates for regeneration
4. Regenerate: `prg analyze . --create-skill pytest-testing-workflow`

**Implementation**: `generator/skill_tracker.py` — thread-safe `SkillTracker` class. `get_low_scoring(threshold=0.3)` returns skills below the threshold that have accumulated at least 3 feedback votes, preventing premature flagging of new skills.

**Use Case**: Continuous quality improvement of your skill library. Skills that helped you solve real problems rise; skills that misfire or produce irrelevant output are flagged automatically.

---

### Feature 13: Watch Mode

**What it does**: Monitors project files for changes and automatically re-runs `prg analyze --incremental` whenever a relevant file is saved. Keeps `.clinerules/` in sync with the codebase without manual intervention.

**Command**:
```bash
prg watch .
prg watch . --delay 5.0          # coalesce saves over 5 seconds instead of 2
prg watch . --ide cursor --quiet # target a specific IDE, suppress non-error output
```

**Monitored files**:
- `README.md`
- `pyproject.toml`, `requirements*.txt`
- `Dockerfile`, `docker-compose.yml`
- `package.json`, `Cargo.toml`, `go.mod`
- All files under `tests/` directories

**Behaviour**:
- 2-second debounce coalesces rapid saves into a single analysis run
- Re-entry guard prevents overlapping runs if analysis takes longer than the debounce window
- Graceful Ctrl+C shutdown with a clean exit message

**Use Case**: Active development sessions where README, dependencies, or tests evolve frequently. Pair with `--quiet` for CI or background terminal use.

---

### Feature 15: Ralph Feature Loop Engine 🔁

**What it does**: A feature-scoped autonomous loop that runs iteratively on a single git branch until a feature is complete — or max iterations are reached. Unlike [Autopilot (Feature 9)](#feature-9-autopilot-), Ralph requires **no human input per iteration**: it self-reviews, runs tests, and keeps going until success criteria are met.

**Commands**:
```bash
# Step 1: Set up a new feature (creates plan, branch, STATE.json)
prg feature "Add loading states to forms"
# Output:
#   features/FEATURE-001/PLAN.md
#   features/FEATURE-001/TASKS.yaml
#   features/FEATURE-001/STATE.json
#   git branch: ralph/FEATURE-001-add-loading-states

# Step 2: Run the autonomous loop
prg ralph run FEATURE-001

# Inspect progress
prg ralph status FEATURE-001

# Resume after an interruption or emergency stop
prg ralph resume FEATURE-001

# Emergency stop
prg ralph stop FEATURE-001 --reason "scope changed"

# Human approval → merge to main
prg ralph approve FEATURE-001
```

**Loop Architecture**:
```
prg feature "Improve UI onboarding"
    ↓
features/FEATURE-001/ created + git branch
    ↓
prg ralph run FEATURE-001   ← [RALPH LOOP]
    iteration 1: context (rules.md + PLAN.md) → skill match → agent → git commit → self-review
    iteration 2: review issues fixed if score < 70 → tests run
    ...
    iteration N: score > 85 + tests pass + no pending tasks → success → PR created
```

**Persistent State (`features/FEATURE-001/STATE.json`)**:
```json
{
  "feature_id": "FEATURE-001",
  "task": "Add loading states to forms",
  "branch_name": "ralph/FEATURE-001-add-loading-states",
  "status": "running",
  "iteration": 3,
  "tasks_total": 5,
  "tasks_complete": 2,
  "max_iterations": 20,
  "last_review_score": 82,
  "test_pass_rate": 1.0,
  "exit_condition": null
}
```

**Exit Conditions**:
| Condition | Behaviour |
|---|---|
| Review score > 85 + tests pass + no pending tasks | `status=success`, PR created |
| Max iterations reached | `status=max_iterations`, PR created with findings |
| Test failures 3× in a row | `status=stopped`, human intervention requested |
| Review score < 60 | `status=stopped` (emergency stop) |
| `prg ralph stop` | `status=stopped`, checkout main |

**How it differs from Autopilot**:

| | Autopilot `prg autopilot` | Ralph `prg ralph run` |
|---|---|---|
| **Scope** | Whole project | Single feature |
| **Human gates** | Every task | Only at `prg ralph approve` |
| **State persistence** | None | `STATE.json` (resumable) |
| **Self-review** | No | Per-iteration (score gate) |
| **Git strategy** | One branch per task | One branch per feature |
| **Iteration limit** | Unlimited (until done) | Configurable (default 20) |

**Integration with existing PRG**:
- Reads `.clinerules/rules.md` as loop context on every iteration
- Uses `AgentExecutor.match_skill()` to auto-trigger relevant skills
- Uses `SelfReviewer` (same as `prg review`) for per-iteration quality gate
- Saves per-iteration critiques to `features/FEATURE-001/CRITIQUES/iter-001.md`

**Use Case**: Autonomous feature development where you want the AI to keep iterating on a single well-scoped change ("Add loading states", "Add caching layer") until it's genuinely done — rather than stopping every task to ask for approval.

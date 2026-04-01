# Features Overview

Project Rules Generator offers a suite of tools to analyze your codebase and generate context-aware rules for AI agents.

## Feature Breakdown

| Feature | Description | Speed | AI Required | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Basic Analysis** | Scans code structure & README for rules | Fast | No | ✅ |
| **AI Skills** | Uses LLM to generate custom skills | Slow | Yes | ✅ |
| **Incremental** | Updates only changed sections | Very Fast | No | ✅ |
| **Task Breakdown** | Breaks large tasks into smaller steps | Medium | Yes | ✅ |
| **Autopilot** | End-to-end discovery & execution loop | Slow | Yes | ✅ |
| **Project Manager** | Lifecycle orchestration (Setup→Verify→Exec→Report) | Slow | Yes | ✅ |
| **Two-Stage Planning** | Design → Plan workflow for complex features | Slow | Yes | ✅ |
| **Constitution** | Generates high-level principles | Fast | No | ✅ |
| **Skill Management** (`--create-skill`, `--list-skills`) | Managing your learned/project skills library | Instant | No | ✅ |
| **`prg init`** | First-run wizard — detect stack, generate rules, print next steps | Fast | No | ✅ |
| **`prg skills list/validate/show`** | Sub-commands for skill inspection and validation | Instant | No | ✅ |
| **Spec Generation** | LLM-generated `spec.md` (Overview, Goals, User Stories, Acceptance Criteria) | Medium | Yes | ✅ |

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

### Feature 9: Autopilot 🤖 NEW
**What it does**: A fully autonomous loop that takes a project from zero to implemented features.

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
4.  **Human Review**: Asks for your approval.
    -   **Yes**: Merges branch.
    -   **No**: Rolls back changes.

**Use Case**: "Hands-off" development for well-defined projects or refactoring tasks.

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


# Features Overview

Project Rules Generator offers a suite of tools to analyze your codebase and generate context-aware rules for AI agents.

## Feature Breakdown

| Feature | Description | Speed | AI Required |
| :--- | :--- | :--- | :--- |
| **Basic Analysis** | Scans code structure & README for rules | Fast | No |
| **AI Skills** | Uses LLM to generate custom skills | Slow | Yes |
| **Incremental** | Updates only changed sections | Very Fast | No |
| **Task Breakdown** | Breaks large tasks into smaller steps | Medium | Yes |
| **Two-Stage Planning** | Design -> Plan workflow for complex features | Slow | Yes |
| **Constitution** | Generates high-level principles | Fast | No |
| **Skill Management** | Managing your learned skills library | Instant | No |

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
prg analyze . --auto-generate-skills --ai --api-key YOUR_KEY
# Or shorter:
prg analyze . --mode ai --api-key YOUR_KEY
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
**Providers**: Gemini (free), Claude (paid).

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
prg analyze . --list-skills

# Add specific skill
prg analyze . --add-skill builtin/brainstorming

# Remove skill
prg analyze . --remove-skill test-driven-development

# Add custom skill from file
prg analyze . --add-skill ~/my-team-workflow.md
```

**Output**:
```
Available skills:
  - test-driven-development (builtin)
  - systematic-debugging (builtin)
  - api-optimization (learned)
```

**Use Case**: Customize exactly which workflows the AI uses for your specific project needs.

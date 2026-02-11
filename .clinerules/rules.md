**CONTEXT**

> The First AI That Learns Your Coding Style

This project uses: python, gemini, claude, click

**ARCHITECTURE**

- **Project type**: python-cli
- **Entry points**: main.py
- **Structural patterns**: python-cli, pytest-tests
- **Languages**: python

**FILE STRUCTURE**

**Entry points:**
- `main.py`

**Detected patterns:**
- python-cli
- pytest-tests

**DEPENDENCIES**

**Python** (11 packages): click, pyyaml, pathspec, pydantic, tqdm, google-generativeai, groq, python-dotenv, gitpython, rich, tomli

**DO (must follow)**

- **Run automated tests before committing**: Use `pytest` to ensure all tests pass.
- **Use type hints for public function signatures**: Add type hints to make code more readable and maintainable.
- **Use Pydantic models for data validation**: Replace raw dictionaries with Pydantic models to ensure data consistency.
- **Use Click decorators for CLI arguments**: Use Click decorators to handle CLI arguments instead of parsing `sys.argv` manually.
- **Follow existing project structure and naming conventions**: Adhere to the existing project structure and naming conventions to ensure consistency.
- **Keep module imports at the top**: Place imports at the top of each module to improve readability.

**DON'T**

- **Avoid using `print()` for logging**: Use the `logging` module for logging instead of `print()`.
- **Don't catch bare `Exception`**: Catch specific exceptions instead of bare `Exception` to ensure accurate error handling.
- **Don't use `sys.exit()` in library code**: Raise exceptions instead of using `sys.exit()` in library code to allow Click to handle exit.
- **Don't commit secrets, API keys, or `.env` files**: Keep sensitive information out of version control.
- **Don't add dependencies without checking license compatibility**: Verify license compatibility before adding dependencies.

**TESTING**

- **Framework**: pytest
- **Test files**: 34 (262 test cases)
- **Test types**: unit, integration
- **Fixtures**: shared via `conftest.py`
- **Test data**: `tests/fixtures/` directory

```bash
# Run all tests
pytest
# Run with coverage
pytest --cov
# Run specific test file
pytest tests/test_specific.py -v
```

**PRIORITIES**

1. **Improve documentation clarity**: Enhance documentation to make it more readable and actionable.
2. **Run automated tests before committing**: Use `pytest` to ensure all tests pass.
3. **Follow existing project structure and naming conventions**: Adhere to the existing project structure and naming conventions to ensure consistency.

**CONTEXT STRATEGY**

### File Loading by Task Type

| Task | Load first | Then load |
|------|-----------|-----------|
| Bug fix | relevant module source | corresponding `test_*.py` file |
| New feature | `main.py` | related modules |
| Refactor | module + its dependents | test suite |
| Writing tests | `conftest.py` + test directory | source module under test |

### Module Groupings

- **main**: `main.py` and its imports

### Exclude from Context

- `**/*.pyc`
- `**/__pycache__/**`
- `**/.venv/**`
- `**/node_modules/**`
- `**/*-skills.md`
- `**/*-skills.json`
- `**/.clinerules*`

**WORKFLOWS**

### Setup
### From Source (Current)
```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e .
```
 
### Verify
```bash
prg --version
```
 
---

### Development
```bash
git checkout -b feat/descriptive-name
# Write code + tests, then run:
pytest
git add .
git commit -m "feat: descriptive message"
```

---

**AGENT SKILLS**

## Active Skill Triggers
- **brainstorming** (builtin): User says: "I want to add...", "Let's build...", "I'm thinking about...", Before any code is written, When requirements are unclear
- **writing-skills** (builtin): User says: "Create a skill for...", "We should formalize...", Repetitive pattern identified, Project has unique workflow in README
- **requesting-code-review** (builtin): Task/feature complete, User says: "Ready for review", "Can you review?", Before creating PR/merge request
- **subagent-driven-development** (builtin): PLAN.md exists and user approves execution, User says: "Execute the plan", "Let's go", "Start implementation"
- **systematic-debugging** (builtin): User reports: "bug", "error", "not working", "failing test", CI/CD failure, Exception in logs
- **test-driven-development** (builtin): New feature implementation, Bug fix, Refactoring
- **writing-plans** (builtin): After design approval (DESIGN.md exists), User says: "Let's implement this", "Create a plan", Before starting implementation

## Skill Definitions

### Skill: brainstorming
# Skill: Brainstorming & Design Refinement

## Purpose
Refine vague ideas into concrete, implementable designs through Socratic questioning.

## Auto-Trigger
- User says: "I want to add...", "Let's build...", "I'm thinking about..."
- Before any code is written
- When requirements are unclear

## Process

### Stage 1: Clarify the Goal
Ask:
1. What problem are you trying to solve?
2. Who is the user/consumer of this feature?
3. What does success look like?

### Stage 2: Explore Alternatives
Present 2-3 approaches with trade-offs:
- Simplest solution
- Most robust solution
- Hybrid approach

### Stage 3: Define Scope
Break down into:
- Must have (MVP)
- Nice to have
- Out of scope (for now)

### Stage 4: Present Design
Show design in digestible chunks (max 10 lines per section):
- Data models
- API contracts
- Key algorithms
- Edge cases

### Stage 5: Get Sign-Off
Wait for explicit approval before proceeding.

## Output
Create `DESIGN.md` with:
- Problem statement
- Chosen approach
- Implementation outline
- Success criteria

## Anti-Patterns
❌ Jumping to implementation without design
❌ Overwhelming user with too much info at once
❌ Not exploring alternatives
❌ Missing edge cases


### Skill: writing-skills
# Meta-Skill: Writing New Skills

## Purpose
Create new skills from project documentation and learned patterns.

## Auto-Trigger
- User says: "Create a skill for...", "We should formalize..."
- Repetitive pattern identified
- Project has unique workflow in README

## Process

### 1. Identify the Pattern
- Does this happen repeatedly?
- Is it documented?
- Would automation help?

### 2. Extract from Documentation
Look for:
- "Always do X before Y"
- "Never do A without B"
- Step-by-step guides
- Best practices sections

### 3. Create SKILL.md Structure

```markdown
# Skill: [Name]

## Purpose
[One sentence: what problem does this solve]

## Auto-Trigger
[When should agent activate this skill]

## Process
[Step-by-step instructions]

## Output
[What artifact/state results]

## Anti-Patterns
❌ [What NOT to do]
```

### 4. Test the Skill
- Create example scenario
- Follow the skill
- Verify output matches expectations
- Refine based on issues

### 5. Save to Directory
- `learned/` for project-specific
- `builtin/` for general-purpose (after validation)

## Anti-Patterns
❌ Creating skill without testing
❌ Vague trigger conditions
❌ Missing anti-patterns section


### Skill: requesting-code-review
# Skill: Requesting Code Review

## Purpose
Ensure code quality through pre-review checklist before asking for human review.

## Auto-Trigger
- Task/feature complete
- User says: "Ready for review", "Can you review?"
- Before creating PR/merge request

## Pre-Review Checklist

### 1. Self-Review
```bash
git diff main...HEAD
```
- ✓ Read every line you changed
- ✓ Remove debug statements
- ✓ Check for commented-out code
- ✓ Verify no secrets/credentials

### 2. Tests
- ✓ All tests pass locally
- ✓ New tests for new features
- ✓ Edge cases covered
- ✓ No skipped/ignored tests without reason

### 3. Code Quality
- ✓ Follows project style guide
- ✓ Functions < 50 lines
- ✓ No TODO/FIXME without ticket reference
- ✓ Docstrings for public APIs

### 4. Documentation
- ✓ README updated if needed
- ✓ API docs updated
- ✓ CHANGELOG.md entry added
- ✓ Comments explain "why", not "what"

### 5. Dependencies
- ✓ No unnecessary dependencies added
- ✓ If new deps: justify in PR description
- ✓ Lock file updated

### 6. Performance
- ✓ No obvious performance issues
- ✓ Database queries optimized
- ✓ No N+1 queries

### 7. Security
- ✓ No SQL injection vectors
- ✓ User input sanitized
- ✓ Authentication/authorization checked
- ✓ No sensitive data in logs

## Review Report Format
```markdown
## Code Review Self-Assessment

### Changes Summary
[Brief description]

### Checklist
- [✓] All tests pass
- [✓] No debug code
- [✓] Documentation updated

### Risks/Notes
[Any concerns or TODOs]

### Files Changed
- [file] (+lines, -lines)

Ready for review: **YES** ✓
```

## Anti-Patterns
❌ Requesting review without running tests
❌ Not reviewing your own code first
❌ Missing context in PR description


### Skill: subagent-driven-development
# Skill: Subagent-Driven Development

## Purpose
Execute implementation plan by dispatching fresh subagents per task, with two-stage review.

## Auto-Trigger
- PLAN.md exists and user approves execution
- User says: "Execute the plan", "Let's go", "Start implementation"

## Process

### For Each Task in PLAN.md:

#### 1. Dispatch Subagent
Create fresh context with:
- Task description only
- Relevant files
- Testing requirements
- NO knowledge of other tasks

#### 2. Subagent Executes
- Implements the task
- Writes/runs tests
- Returns code + test results

#### 3. Two-Stage Review

**Stage 1: Spec Compliance**
✓ Does it match task requirements?
✓ Are all files modified as specified?
✓ Do tests pass?
❌ If no → reject, provide feedback, retry

**Stage 2: Code Quality**
✓ Follows project conventions?
✓ Handles edge cases?
✓ No obvious bugs?
✓ Code is readable?
❌ If no → request improvements

#### 4. Commit
```bash
git add [files]
git commit -m "Task N: [brief description]"
```

### 5. Report Progress
✅ Task 1: Setup database schema (3min)
✅ Task 2: Create API endpoint (4min)
🔄 Task 3: In progress...

### Stopping Conditions
- All tasks complete
- Critical issue found (escalate to user)
- Subagent fails 3 times (escalate)

## Anti-Patterns
❌ Giving subagent entire codebase context
❌ Skipping Stage 1 review
❌ Continuing after failed tests
❌ Not committing after each task


### Skill: systematic-debugging
# Skill: Systematic Debugging

## Purpose
Find root cause of bugs through 5-phase structured process.

## Auto-Trigger
- User reports: "bug", "error", "not working", "failing test"
- CI/CD failure
- Exception in logs

## 5-Phase Process

### Phase 1: Reproduce
1. Get exact steps to reproduce
2. Identify expected vs actual behavior
3. Create minimal failing test
4. Verify reproduction consistently
**Output**: Failing test that isolates the bug

### Phase 2: Locate
Use techniques to find *where* it breaks:
- **Binary Search**: Comment out half the code
- **Trace Backwards**: From error to source
- **Instrumentation**: Log state before/after suspected lines
**Output**: Exact line causing bug

### Phase 3: Analyze
Understand *why* it breaks:
- Check assumptions
- Verify data types
- Review recent changes
**Output**: Root cause explanation

### Phase 4: Fix
1. **Immediate Fix**: Correct the logic
2. **Defense in Depth**: Add input validation/guards
3. **Monitoring**: Add logging if needed
**Output**: Committed fix

### Phase 5: Verify
1. Failing test now passes
2. All other tests still pass (regression check)
3. Manual verification
**Output**: Verified green build

## Anti-Patterns
❌ Guessing without reproducing
❌ Fixing symptoms without finding root cause
❌ precise line not identified in stack trace
❌ Declaring "fixed" without verification


### Skill: test-driven-development
# Skill: Test-Driven Development

## Purpose
Enforce RED-GREEN-REFACTOR cycle for all new code.

## Auto-Trigger
- New feature implementation
- Bug fix
- Refactoring

## RED-GREEN-REFACTOR Cycle

### 🔴 RED: Write Failing Test
1. Write test for desired behavior
2. Run test → verify it FAILS
3. Commit: `git commit -m "RED: test for [feature]"`

### 🟢 GREEN: Make It Pass
1. Write minimal code to pass test
2. Run test → verify
# project-rules-generator
## Documentation
### Purpose
This document outlines the coding and contribution rules for the project-rules-generator project.

### Version
2.0

### Generated
Auto-generated

### Project Type
Python CLI

### Project Grounding
This project uses Python, Gemini, Claude, and Click. The project is structured as a Python CLI application with a main entry point in `main.py`. The project follows the pytest-test framework for testing.

## Context
### Project Overview
The project-rules-generator project aims to provide a set of rules and guidelines for coding and contributing to the project. The project uses a combination of Python, Gemini, Claude, and Click to generate rules and automate tasks.

### Project Goals
The primary goals of the project are to:

* Provide a set of rules and guidelines for coding and contributing to the project
* Automate tasks and generate rules using Python, Gemini, Claude, and Click
* Improve code quality and consistency throughout the project

### Concrete Examples
To illustrate these goals, consider the following scenarios:

* A developer wants to implement a new feature, but is unsure of the best approach. The project's rules and guidelines can provide a clear path forward, ensuring that the feature is implemented correctly and efficiently.
* A contributor wants to make changes to the project's codebase, but is unsure of the impact of their changes. The project's rules and guidelines can provide a clear understanding of the project's architecture and dependencies, ensuring that changes are made safely and effectively.

## Architecture
### Project Structure
The project is structured as a Python CLI application with a main entry point in `main.py`. The project follows the pytest-test framework for testing.

### Dependencies
The project uses the following dependencies:

* Click: for building the CLI interface
* PyYAML: for parsing YAML files
* Pathspec: for parsing file paths
* Pydantic: for data validation
* Tqdm: for displaying progress bars
* Google-GenerativeAI: for generating AI-powered rules
* Groq: for generating Groovy code
* Python-dotenv: for loading environment variables
* Gitpython: for interacting with Git repositories
* Rich: for displaying rich text

## File Structure
### Entry Points
* `main.py`: the main entry point of the project

### Detected Patterns
* Python CLI: the project follows the Python CLI pattern
* Pytest-tests: the project uses the pytest-test framework for testing

## Dependencies
### Python Dependencies
The project uses the following Python dependencies:

* Click: for building the CLI interface
* PyYAML: for parsing YAML files
* Pathspec: for parsing file paths
* Pydantic: for data validation
* Tqdm: for displaying progress bars
* Google-GenerativeAI: for generating AI-powered rules
* Groq: for generating Groovy code
* Python-dotenv: for loading environment variables
* Gitpython: for interacting with Git repositories
* Rich: for displaying rich text

## Do (Must Follow)
### Coding Rules
* Run `pytest` before committing: ensure that all tests pass before committing code
* Use type hints on all public function signatures: use type hints to specify the types of function parameters and return values
* Use Pydantic models for data validation: use Pydantic models to validate data and ensure that it conforms to the expected format
* Use Click decorators for CLI arguments: use Click decorators to specify the CLI arguments and options
* Follow existing project structure and naming conventions: follow the existing project structure and naming conventions to ensure consistency
* Keep module imports at file top: keep module imports at the top of each file to ensure that they are easily visible

### Concrete Examples
To illustrate these coding rules, consider the following examples:

* A developer wants to add a new function to the project's codebase. They should use type hints to specify the function's parameters and return values, and use Pydantic models to validate the function's input data.
* A contributor wants to make changes to the project's CLI interface. They should use Click decorators to specify the CLI arguments and options, and follow the existing project structure and naming conventions to ensure consistency.

## Don't
### Coding Rules
* Don't use `print()` for logging: use the `logging` module to log messages instead of using `print()`
* Don't catch bare `Exception`: catch specific exceptions instead of catching the bare `Exception` class
* Don't use `sys.exit()` in library code: raise exceptions instead of using `sys.exit()` in library code
* Don't commit secrets, API keys, or `.env` files: commit secrets, API keys, or `.env` files are sensitive information that should not be committed to the repository

### Concrete Examples
To illustrate these coding rules, consider the following examples:

* A developer wants to log a message to the console. They should use the `logging` module to log the message, rather than using `print()`.
* A contributor wants to catch an exception in their code. They should catch a specific exception, rather than catching the bare `Exception` class.

## Testing
### Framework
The project uses the pytest-test framework for testing.

### Test Files
The project has 35 test files with a total of 272 test cases.

### Test Types
The project uses both unit and integration tests.

### Fixtures
The project uses shared fixtures via `conftest.py`.

### Test Data
The project uses the `tests/fixtures/` directory to store test data.

## Priorities
### Stop Copy-Pasting Generic Rules
The project should focus on using AI-powered rules to generate rules and automate tasks instead of copy-pasting generic rules.

### Run `pip install project-rules-generator`
The project should be installed using the `pip install` command.

### Documentation Clarity
The project documentation should be clear and concise to ensure that users can easily understand the rules and guidelines.

## Context Strategy
### File Loading by Task Type
The project should load files based on the task type to ensure that the correct files are loaded for each task.

| Task | Load first | Then load |
|------|-----------|-----------|
| Bug fix | relevant module source | corresponding `test_*.py` file |
| New feature | `main.py` | related modules |
| Refactor | module + its dependents | test suite |
| Writing tests | `conftest.py` + test directory | source module under test |

### Module Groupings
The project should group modules based on their functionality to ensure that related modules are easily accessible.

* `main`: `main.py` and its imports

### Exclude from Context
The project should exclude certain files and directories from the context to ensure that they are not loaded unnecessarily.

* `**/*.pyc`
* `**/__pycache__/**`
* `**/.venv/**`
* `**/node_modules/**`
* `**/*-skills.md`
* `**/*-skills.json`
* `**/.clinerules*`

## Workflows
### Setup
### From Source (Current)
```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e .

### Verify
```bash
prg --version

### Development
```bash
git checkout -b feat/descriptive-name
# Write code + tests, then run:
pytest
git add .
git commit -m "feat: descriptive message"

## Agent Skills
### Active Skill Triggers
The project should use the following active skill triggers to automate tasks and generate rules.

* `brainstorming` (builtin): User says: "I want to add...", "Let's build...", "I'm thinking about...", Before any code is written, When requirements are unclear
* `writing-skills` (builtin): User says: "Create a skill for...", "We should formalize...", Repetitive pattern identified, Project has unique workflow in README
* `requesting-code-review` (builtin): Task/feature complete, User says: "Ready for review", "Can you review?", Before creating PR/merge request
* `subagent-driven-development` (builtin): PLAN.md exists and user approves execution, User says: "Execute the plan", "Let's go", "Start implementation"
* `systematic-debugging` (builtin): User reports: "bug", "error", "not working", "failing test", CI/CD failure, Exception in logs
* `test-driven-development` (builtin): New feature implementation, Bug fix, Refactoring
* `writing-plans` (builtin): After design approval (DESIGN.md exists), User says: "Let's implement this", "Create a plan", Before starting implementation

## Skill Definitions
### Skill: Brainstorming & Design Refinement

#### Purpose
Refine vague ideas into concrete, implementable designs through Socratic questioning.

#### Auto-Trigger
- User says: "I want to add...", "Let's build...", "I'm thinking about..."
- Before any code is written
- When requirements are unclear

#### Process

#### Stage 1: Clarify the Goal
Ask:
1. What problem are you trying to solve?
2. Who is the user/consumer of this feature?
3. What does success look like?

#### Stage 2: Explore Alternatives
Present 2-3 approaches with trade-offs:
- Simplest solution
- Most robust solution
- Hybrid approach

#### Stage 3: Define Scope
Break down into:
- Must have (MVP)
- Nice to have
- Out of scope (for now)

#### Stage 4: Present Design
Show design in digestible chunks (max 10 lines per section):
- Data models
- API contracts
- Key algorithms
- Edge cases

#### Stage 5: Get Sign-Off
Wait for explicit approval before proceeding.

#### Output
Create `DESIGN.md` with:
- Problem statement
- Chosen approach
- Implementation outline
- Success criteria

#### Anti-Patterns
❌ Jumping to implementation without design
❌ Overwhelming user with too much info at once
❌ Not exploring alternatives
❌ Missing edge cases

### Skill: Writing New Skills

#### Purpose
Create new skills from project documentation and learned patterns.

#### Auto-Trigger
- User says: "Create a skill for...", "We should formalize..."
- Repetitive pattern identified
- Project has unique workflow in README

#### Process

#### 1. Identify the Pattern
- Does this happen repeatedly?
- Is it documented?
- Would automation help?

#### 2. Extract from Documentation
Look for:
- "Always do X before Y"
- "Never do A without B"
- Step-by-step guides
- Best practices sections

#### 3. Create SKILL.md Structure

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

#### 4. Test the Skill
- Create example scenario
- Follow the skill
- Verify output matches expectations
- Refine based on issues

#### 5. Save to Directory
- `learned/` for project-specific
- `builtin/` for general-purpose (after validation)

#### Anti-Patterns
❌ Creating skill without testing
❌ Vague trigger conditions
❌ Missing anti-patterns section

### Skill: Requesting Code Review

#### Purpose
Ensure code quality through pre-review checklist before asking for human review.

#### Auto-Trigger
- Task/feature complete
- User says: "Ready for review", "Can you review?"
- Before creating PR/merge request

#### Pre-Review Checklist

#### 1. Self-Review
```bash
git diff main...HEAD
- ✓ Read every line you changed
- ✓ Remove debug statements
- ✓ Check for commented-out code
- ✓ Verify no secrets/credentials

#### 2. Tests
- ✓ All tests pass locally
- ✓ New tests for new features
- ✓ Edge cases covered
- ✓ No skipped/ignored tests without reason

#### 3. Code Quality
- ✓ Follows project style guide
- ✓ Functions < 50 lines
- ✓ No TODO/FIXME without ticket reference
- ✓ Docstrings for public APIs

#### 4. Documentation
- ✓ README updated if needed
- ✓ API docs updated
- ✓ CHANGELOG.md entry added
- ✓ Comments explain "why", not "what"

#### 5. Dependencies
- ✓ No unnecessary dependencies added
- ✓ If new deps: justify in PR description
- ✓ Lock file updated

#### 6. Performance
- ✓ No obvious performance issues
- ✓ Database queries optimized
- ✓ No N+1 queries

#### 7. Security
- ✓ No SQL injection vectors
- ✓ User input sanitized
- ✓ Authentication/authorization checked
- ✓ No sensitive data in logs

#### Review Report Format
## Code Review Self-Assessment

#### Changes Summary
[Brief description]

#### Checklist
- [✓] All tests pass
- [✓] No debug code
- [✓] Documentation updated

#### Risks/Notes
[Any concerns or TODOs]

#### Files Changed
- [file] (+lines, -lines)

Ready for review: **YES** ✓

#### Anti-Patterns
❌ Requesting review without running tests
❌ Not reviewing your own code first
❌ Missing context in PR description

### Skill: Subagent-Driven Development

#### Purpose
Execute implementation plan by dispatching fresh subagents per task, with two-stage review.

#### Auto-Trigger
- PLAN.md exists and user approves execution
- User says: "Execute the plan", "Let's go", "Start implementation"

#### Process

#### For Each Task in PLAN.md:

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

#### 5. Report Progress
✅ Task 1: Setup database schema (3min)
✅ Task 2: Create API endpoint (4min)
🔄 Task 3: In progress...

#### Stopping Conditions
- All tasks complete
- Critical issue found (escalate to user)
- Subagent fails 3 times (escalate)

#### Anti-Patterns
❌ Giving subagent entire codebase context
❌ Skipping Stage 1 review
❌ Continuing after failed tests
❌ Not committing after each task

### Skill: Systematic Debugging

#### Purpose
Find root cause of bugs through 5-phase structured process.

#### Auto-Trigger
- User reports: "bug", "error", "not working", "failing test"
- CI/CD failure
- Exception in logs

#### 5-Phase Process

#### Phase 1: Reproduce
1. Get exact steps to reproduce
2. Identify expected vs actual behavior
3. Create minimal failing test
4. Verify reproduction consistently
**Output**: Failing test that isolates the bug

#### Phase 2: Locate
Use techniques to find *where* it breaks:
- **Binary Search**: Comment out half the code
- **Trace Backwards**: From error to source
- **Instrumentation**: Log state before/after suspected lines
**Output**: Exact line causing bug

#### Phase 3: Analyze
Understand *why* it breaks:
- Check assumptions
- Verify data types
- Review recent changes
**Output**: Root cause explanation

#### Phase 4: Fix
1. **Immediate Fix**: Correct the logic
2. **Defense in Depth**: Add input validation/guards
3. **Monitoring**: Add logging if needed
**Output**: Committed fix

#### Phase 5: Verify
1. Failing test now passes
2. All other tests still pass (regression check)
3. Manual verification
**Output**: Verified green build

#### Anti-Patterns
❌ Guessing without reproducing
❌ Fixing symptoms without finding root cause
❌ precise line not identified in stack trace
❌ Declaring "fixed" without verification

### Skill: Test-Driven Development

#### Purpose
Enforce RED-GREEN-REFACTOR cycle for all new code.

#### Auto-Trigger
- New feature implementation
- Bug fix
- Refactoring

#### RED-GREEN-REFACTOR Cycle

#### 🔴 RED: Write Failing Test
1. Write test for desired behavior
2. Run test → verify it FAILS
3. Commit: `git commit -m "RED: test for [feature]"`

#### 🟢 GREEN: Make It Pass
1. Write minimal code to pass test
2. Run test → verify it PASSES
3. All other tests still pass
4. Commit: `git commit -m "GREEN: implement [feature]"`

#### 🔵 REFACTOR: Clean Up
1. Improve code quality (no behavior change)
2. Run all tests → verify they PASS
3. Commit: `git commit -m "REFACTOR: clean up [feature]"`

#### Rules
✅ ALWAYS write test first
✅ Run test and see it fail before writing code
✅ Write minimal code to pass
✅ Commit after each phase
❌ NEVER write code before test
❌ NEVER skip the RED phase
❌ NEVER refactor without passing tests

#### Anti-Patterns
❌ Writing code then adding tests
❌ Not verifying test fails first
❌ Writing too much code at once
❌ Skipping refactor phase

### Skill: Writing Implementation Plans

#### Purpose
Break approved designs into bite-sized, executable tasks (2-5 minutes each).

#### Auto-Trigger
- After design approval (DESIGN.md exists)
- User says: "Let's implement this", "Create a plan"
- Before starting implementation

#### Task Structure
Each task must include:
1. **Goal**: One-sentence objective
2. **Files**: Exact paths to modify/create
3. **Changes**: Specific code snippets or logic
4. **Tests**: How to verify it works
5. **Dependencies**: Which tasks must complete first

#### Task Size Guidelines
✅ 2-5 minutes per task
✅ Single responsibility
✅ Independently testable
❌ "Refactor the entire module" (too big)
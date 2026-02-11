# Project Rules Generator
==========================

## Project Overview
-------------------

### Project Information

* **Project Name**: project-rules-generator
* **Purpose**: Establish coding and contribution rules for this workspace
* **Version**: 2.0
* **Generated**: Automatically
* **Project Type**: Python Command-Line Interface (CLI)

## Context
---------

### Project Description

The project utilizes AI technologies to learn and adapt to your coding style, enhancing development efficiency and productivity. This project leverages Python, Gemini, Claude, and Click to achieve its goals.

### Technologies Used

* **Python**: A high-level, interpreted programming language used for general-purpose programming.
* **Gemini**: An AI-powered platform for building conversational interfaces.
* **Claude**: An AI development platform that enables the creation of custom AI models.
* **Click**: A Python package for creating command-line interfaces (CLI).

## Architecture
-------------

### Project Structure

* **Project Type**: Python CLI
* **Entry Points**: `main.py`
* **Structural Patterns**: Python CLI, Pytest Tests
* **Languages**: Python

## File Structure
-----------------

### Entry Points

* **`main.py`**: The primary entry point of the project, responsible for executing the CLI.

### Detected Patterns

* **Python CLI**: A pattern used for creating command-line interfaces.
* **Pytest Tests**: A pattern used for writing unit tests and integration tests.

## Dependencies
-------------

### Python Packages

* **Click**: A package for creating command-line interfaces.
* **PyYAML**: A package for parsing and generating YAML files.
* **PathSpec**: A package for working with file paths.
* **Pydantic**: A package for data validation and modeling.
* **TQDM**: A package for progress bars.
* **Google-GenerativeAI**: A package for AI-powered text generation.
* **Groq**: A package for querying and manipulating data.
* **Python-Dotenv**: A package for loading environment variables from files.
* **GitPython**: A package for interacting with Git repositories.
* **Rich**: A package for formatting and displaying text.
* **Tomli**: A package for parsing and generating TOML files.

## Rules
--------

### Table of Contents

* [Do (Must Follow)](#do-must-follow)
* [Don't (Must Avoid)](#dont-must-avoid)

### Do (Must Follow)
#### 1. Run `pytest` before committing

* **Step-by-Step Guide**:
  1. Open your terminal or command prompt.
  2. Navigate to the project directory.
  3. Run `pytest` to execute all tests.
  4. Check the test results and fix any failures.
  5. Commit your changes once all tests pass.

#### 2. Use type hints on all public function signatures

* **Example**:
  ```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
* **Step-by-Step Guide**:
  1. Identify public functions in your code.
  2. Add type hints to function signatures.
  3. Use the `str` type for string parameters and return types.

#### 3. Use Pydantic models for data validation

* **Example**:
  ```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
* **Step-by-Step Guide**:
  1. Install Pydantic using pip.
  2. Define Pydantic models for data validation.
  3. Use Pydantic models to validate data in your code.

#### 4. Use Click decorators for CLI arguments

* **Example**:
  ```python
import click

@click.command()
@click.option("--name", help="Your name")
def greet(name):
    print(f"Hello, {name}!")
* **Step-by-Step Guide**:
  1. Install Click using pip.
  2. Define Click decorators for CLI arguments.
  3. Use Click decorators to define CLI arguments and options.

#### 5. Follow existing project structure and naming conventions

* **Example**:
  ```python
# Existing project structure
project/
main.py
models/
user.py
__init__.py
* **Step-by-Step Guide**:
  1. Familiarize yourself with the existing project structure.
  2. Adhere to the established project structure and naming conventions.

#### 6. Keep module imports at file top

* **Example**:
  ```python
# Correct import placement
import os
import sys

# Incorrect import placement
def main():
    import os
    import sys
* **Step-by-Step Guide**:
  1. Identify module imports in your code.
  2. Place module imports at the top of each file.

### Don't (Must Avoid)
#### 1. Avoid using global variables

* **Example**:
  ```python
x = 5  # Global variable

def add(y):
    return x + y
* **Step-by-Step Guide**:
  1. Identify global variables in your code.
  2. Replace global variables with function arguments or return values.

#### 2. Avoid using mutable default arguments

* **Example**:
  ```python
def greet(name, options={}):
    options['greeting'] = 'Hello'
    print(options)
* **Step-by-Step Guide**:
  1. Identify mutable default arguments in your code.
  2. Use immutable default arguments instead.

#### 3. Avoid using `print` statements for debugging

* **Example**:
  ```python
# Incorrect debugging code
print(x)
* **Step-by-Step Guide**:
  1. Identify `print` statements in your code.
  2. Use a debugger or logging statements instead.

on't

* **Don't use `print()` for logging**: Use the `logging` module for logging instead of `print()`.
* **Don't catch bare `Exception`**: Catch specific exceptions instead of bare `Exception`.
* **Don't use `sys.exit()` in library code**: Raise exceptions instead of using `sys.exit()` in library code.
* **Don't commit secrets, API keys, or `.env` files**: Keep sensitive information out of version control.
* **Don't add dependencies without checking license compatibility**: Ensure that new dependencies have compatible licenses.

## Testing
---------

### Testing Framework

* **Pytest**: A testing framework for Python.

### Test Files

* 35 test files (272 test cases)

### Test Types

* **Unit Tests**: Test individual units of code.
* **Integration Tests**: Test interactions between multiple units of code.

### Fixtures

* **Shared via `conftest.py`**: Shared fixtures are defined in `conftest.py`.

### Test Data

* **`tests/fixtures/` directory**: Test data is stored in the `tests/fixtures/` directory.

### Running Tests

```bash
# Run all tests
pytest
# Run with coverage
pytest --cov
# Run specific test file
pytest tests/test_specific.py -v

## Priorities
-------------

1. **Improve AI-powered project rules**: Develop AI-powered project rules that adapt to your coding style.
2. **Enhance documentation clarity**: Improve documentation clarity and organization.
3. **Install project rules generator**: Install the project rules generator using pip.

## Context Strategy
------------------

### File Loading by Task Type

| Task | Load first | Then load |
|------|-----------|-----------|
| Bug fix | Relevant module source | Corresponding `test_*.py` file |
| New feature | `main.py` | Related modules |
| Refactor | Module + its dependents | Test suite |
| Writing tests | `conftest.py` + test directory | Source module under test |

### Module Groupings

* **`main`**: `main.py` and its imports

### Exclude from Context

* **`**/*.pyc`**: Exclude compiled Python files.
* **`**/__pycache__/**`: Exclude Python cache directories.
* **`**/.venv/**`: Exclude virtual environment directories.
* **`**/node_modules/**`: Exclude Node.js module directories.
* **`**/*-skills.md`**: Exclude skills documentation files.
* **`**/*-skills.json`**: Exclude skills JSON files.
* **`**/.clinerules*`**: Exclude Clinerules files.

## Workflows
------------

### Setup

### From Source (Current)

```bash
git clone https://

github.com/Amitro123/project-rules-generator
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
--------------

### Active Skill Triggers

* **brainstorming** (builtin): User says: "I want to"

 add...", "Let's build...", "I'm thinking about...", Before any code is written, When requirements are unclear
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
2. Run test → verify it PASSES
3. All other tests still pass
4. Commit: `git commit -m "GREEN: implement [feature]"`

### 🔵 REFACTOR: Clean Up
1. Improve code quality (no behavior change)
2. Run all tests → verify they PASS
3. Commit: `git commit -m "REFACTOR: clean up [feature]"`

## Rules
✅ ALWAYS write test first
✅ Run test and see it fail before writing code
✅ Write minimal code to pass
✅ Commit after each phase
❌ NEVER write code before test
❌ NEVER skip the RED phase
❌ NEVER refactor without passing tests

## Anti-Patterns
❌ Writing code then adding tests
❌ Not verifying test fails first
❌ Writing too much code at once
❌ Skipping refactor phase


### Skill: writing-plans
# Skill: Writing Implementation Plans

## Purpose
Break approved designs into bite-sized, executable tasks (2-5 minutes each).

## Auto-Trigger
- After design approval (DESIGN.md exists)
- User says: "Let's implement this", "Create a plan"
- Before starting implementation

## Process

### Task Structure
Each task must include:
1. **Goal**: One-sentence objective
2. **Files**: Exact paths to modify/create
3. **Changes**: Specific code snippets or logic
4. **Tests**: How to verify it works
5. **Dependencies**: Which tasks must complete first

### Task Size Guidelines
✅ 2-5 minutes per task
✅ Single responsibility
✅ Independently testable
❌ "Refactor the entire module" (too big)
❌ "Add a comment" (too small)

### Plan Format
Task 1: [Title]
Dependencies: [Task IDs or "None"]
Files: [exact paths]
Changes:

[specific change 1]

[specific change 2]
Tests: [how to verify]
Estimated time: [X min]

## Output
Create `PLAN.md` in project root with all tasks.

## Anti-Patterns
❌ Vague task descriptions
❌ Tasks without test criteria
❌ Missing file paths
❌ Tasks that take > 10 minutes
❌ Unclear dependencies
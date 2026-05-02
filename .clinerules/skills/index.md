---
project: project-rules-generator
purpose: Agent skills for this project
type: agent-skills
detected_type: agent
confidence: 1.00
version: 1.0
---

## PROJECT CONTEXT
- **Type**: Agent
- **Domain**: Auto-generated skills index for project-rules-generator

## SKILLS INDEX

### BUILTIN SKILLS

#### brainstorming
name: brainstorming

**Triggers:** User says: "I want to add...", "Let's build...", "I'm thinking about...", Before any code is written, When requirements are unclear
**Tools:** read, exec
**Command:** `prg brainstorming`
**Input/Output:** Output: Create `DESIGN.md` with:
- Problem statement
- Chosen approach
- Implementation outline
- Success criteria

```bash
# Verify DESIGN.md was created after the session
cat DESIGN.md
```

#### ci-lint-failures
name: ci-lint-failures

**Triggers:** "ci lint failure", "github actions lint error", "fix linting in ci", "pipeline lint error"
**Tools:** read, exec
**Command:** `prg ci-lint-failures`
**Input/Output:** Output: - A clean Git working directory, free of linting errors.
- A passing GitHub Actions pipeline, indicating successful linting.
- Modified project source files with corrected code style and quality issues.

#### requesting-code-review
name: requesting-code-review

**Triggers:** Task/feature complete, User says: "Ready for review", "Can you review?", Before creating PR/merge request
**Tools:** read, exec
**Command:** `prg requesting-code-review`
**Input/Output:** Output: ```markdown

#### subagent-driven-development
name: subagent-driven-development

**Triggers:** PLAN.md exists and user approves execution, User says: "Execute the plan", "Let's go", "Start implementation", After `prg plan` generates a task list
**Tools:** read, exec
**Command:** `prg subagent-driven-development`
**Input/Output:** Output: Each task produces: committed code, passing tests, and a progress entry in the session log.

#### systematic-debugging
name: systematic-debugging

**Triggers:** User reports: "bug", "error", "not working", "failing test", CI/CD failure, Exception in logs
**Tools:** read, exec
**Command:** `prg systematic-debugging`
**Input/Output:** Output: - Committed fix with root-cause explanation in commit message
- Minimal failing test that will catch regressions
- Green CI build

#### test-driven-development
name: test-driven-development

**Triggers:** New feature implementation, Bug fix, Refactoring
**Tools:** read, exec
**Command:** `prg test-driven-development`
**Input/Output:** Output: - Passing test suite with new test covering the feature
- Committed code in three phases (RED, GREEN, REFACTOR)
- Test that will catch future regressions

#### writing-plans
name: writing-plans

**Triggers:** After design approval (DESIGN.md exists), User says: "Let's implement this", "Create a plan", Before starting implementation
**Tools:** read, exec
**Command:** `prg writing-plans`
**Input/Output:** Output: `PLAN.md` in project root with all tasks, ready for `prg plan --from-design DESIGN.md`.

#### writing-skills
Create new skills from project documentation and learned patterns.

**Triggers:** User says: "Create a skill for...", "We should formalize...", Repetitive pattern identified, Project has unique workflow in README
**Tools:** read, exec
**Command:** `prg writing-skills`
**Input/Output:** Output: [What artifact/state results]

### LEARNED SKILLS

#### api-client-patterns
name: api-client-patterns

**Triggers:** "API client", "LLM provider", "model integration", "credentials", "API key", "new command with LLM"
**Tools:** read, exec
**Command:** `prg api-client-patterns`
**Input/Output:** Standard CLI I/O

#### architecture-improvements
﻿---

**Triggers:** "improve architecture", "refactor project structure", "best practices for python design"
**Tools:** read, exec
**Command:** `prg architecture-improvements`
**Input/Output:** Output: - Improved code readability and maintainability.
- A more modular and scalable project structure.
- Potentially updated `requirements.txt` or `pyproject.toml` if dependencies change.
- Verified GitHub Actions workflows that correctly build and test the refactored project.

#### argparse-patterns
name: argparse-patterns

**Triggers:** "how to add a new cli command", "argparse example", "command line arguments", "define a new cli", "cli patterns"
**Tools:** read, exec
**Command:** `prg argparse-patterns`
**Input/Output:** Standard CLI I/O

#### branch-management
name: branch-management

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg branch-management`
**Input/Output:** Standard CLI I/O

#### cleanup
name: cleanup

**Triggers:** "cleanup"**, **"clean project"**, **"clear cache", "remove artifacts"**, **"fresh start"**, **"stale cache", Before running a full `pytest` suite to rule out cache-poisoned results, Before building or publishing a new `dist/` package, 
**Tools:** read, exec
**Command:** `prg cleanup`
**Input/Output:** Output: After a successful cleanup:
- No `__pycache__` or `.pyc` files remain in any subdirectory
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache` are gone
- `build/`, `dist/`, `*.egg-info/` are removed
- `.coverage` and `htmlcov/` are removed
- `pytest` passes the full suite from a cold cache (no tests lost to cleanup)

---

#### cli-testing
﻿---

**Triggers:** User mentions: "cli", "testing"
**Tools:** read, exec
**Command:** `prg cli-testing`
**Input/Output:** Output: Applying this skill produces:

- Updated or created files following `cli testing` patterns
- Status report with changes made
- Recommendations for next steps

#### click-commands
name: click-commands

**Triggers:** "add new cli command", "create click command", "register cli tool"
**Tools:** read, exec
**Command:** `prg click-commands`
**Input/Output:** Standard CLI I/O

#### code-duplication
﻿---

**Triggers:** "code duplication", "duplicate code", "refactor repetitive code"
**Tools:** read, exec
**Command:** `prg code-duplication`
**Input/Output:** Output: - Reduced lines of code in the project.
- Improved code readability and maintainability.
- Passing local tests and successful GitHub Actions CI builds.
- Potentially new or modified Python files (e.g., `utils.py` for common functions) and updated existing files (e.g., `main.py` if it uses the common logic).

#### code-review
name: code-review

**Triggers:** "review this code", "perform a code review", "check code quality", "feedback on pull request"
**Tools:** read, exec
**Command:** `prg code-review`
**Input/Output:** Output: - A comprehensive set of comments and suggestions on the reviewed code.
- Identified potential bugs, performance issues, or architectural concerns.
- Confirmation that the code adheres to project standards and best practices.
- An approved Pull Request or a list of required changes for the author.

#### config-management
name: config-management

**Triggers:** "manage config", "update configuration", "config settings"
**Tools:** read, exec
**Command:** `prg config-management`
**Input/Output:** Output: - A consistent, type-safe `RootConfig` Pydantic object (or its dictionary representation) containing all validated application settings.
- Increased confidence that configuration is correctly parsed and applied.

#### coverage-patterns
name: coverage-patterns

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg coverage-patterns`
**Input/Output:** Standard CLI I/O

#### dead-code
﻿---

**Triggers:** "remove dead code", "clean up unused code", "refactor for dead code"
**Tools:** read, exec
**Command:** `prg dead-code`
**Input/Output:** Output: - A cleaner, more maintainable Python codebase.
- Modified `.py` files with dead code removed.
- Confirmation that existing tests still pass after removal.

#### diff-patterns
name: diff-patterns

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg diff-patterns`
**Input/Output:** Standard CLI I/O

#### docker-deployment
name: docker-deployment

**Triggers:** "docker deployment", "docker", "deployment"
**Tools:** read, exec
**Command:** `prg docker-deployment`
**Input/Output:** Output: [What artifact or state results from applying this skill.]

#### error-handling
name: error-handling

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg error-handling`
**Input/Output:** Standard CLI I/O

#### exception-narrower
name: exception-narrower

**Triggers:** "find all broad exception handlers", "narrow catch-all blocks", "stop swallowing exceptions", "make failures more visible"
**Tools:** read, exec
**Command:** `prg exception-narrower`
**Input/Output:** Output: - Grep report of all broad catches with classification
- Narrowed exception types in internal logic paths
- Preserved (and documented) broad catches at system boundaries
- All tests still pass

#### fixture-patterns
name: fixture-patterns

**Triggers:** "pytest fixture", "test setup", "shared test data", "test environment", "conftest.py"
**Tools:** read, exec
**Command:** `prg fixture-patterns`
**Input/Output:** Standard CLI I/O

#### gemini-api-integration
﻿---

**Triggers:** "integrate gemini api", "gemini api key", "how to use gemini model"
**Tools:** read, exec
**Command:** `prg gemini-api-integration`
**Input/Output:** Output: - A more secure method for handling the Gemini API key.
- A well-structured and modular approach to interacting with the Gemini API.
- Code examples demonstrating best practices for API client initialization and API calls with error handling.

#### god-function-refactor
name: god-function-refactor

**Triggers:** "break up analyze_cmd.py", "split the analyze command into services", "reduce god-function complexity", "extract orchestration from CLI handler"
**Tools:** read, exec
**Command:** `prg god-function-refactor`
**Input/Output:** Output: - `cli/analyze_cmd.py` reduced to option parsing + orchestration calls (< 100 lines ideal)
- New/updated helper modules each with a single clear responsibility
- All existing tests still pass

#### httpx-client
﻿---

**Triggers:** "httpx client", Project Context Signals:, `has_ci`, `has_tests` Γזע Test suite available, `has_docs`, `has_api` Γזע API endpoints present
**Tools:** read, exec
**Command:** `prg httpx-client`
**Input/Output:** Output: This skill generates:


- Modified/created files in `/`
- Status report with changes
- Recommendations for next steps

#### logging-best-practices
﻿---

**Triggers:** "logging best practices", Project Context Signals:, `has_docs`, `has_api` — API endpoints present, `has_tests` — Test suite available, `has_ci`
**Tools:** read, exec
**Command:** `prg logging-best-practices`
**Input/Output:** Output: This skill generates:


- Modified/created files in `project-rules-generator/`
- Status report with changes
- Recommendations for next steps

#### manual-qa
﻿---

**Triggers:** User mentions: "manual qa", "qa pass", "quality check", User asks to "verify", "validate", or "regression check" the project, After merging a PR or applying a code review fix, Working in: `generator/analyzers/readme_parser.py`, `generator/skill_*.py`, `cli/`, 
**Tools:** read, exec
**Command:** `prg manual-qa`
**Input/Output:** Output: - QA report (fill in the table above)
- List of any regressions found with file + line number
- Go/No-Go decision for release

---

#### mocking-patterns
name: mocking-patterns

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg mocking-patterns`
**Input/Output:** Standard CLI I/O

#### operation-adder
﻿---

**Triggers:** User mentions: "operation", "adder", FFmpeg operations needed, Working in frontend code: *.tsx, *.jsx, *.ts, Working in backend code: *.py
**Tools:** read, exec
**Command:** `prg operation-adder`
**Input/Output:** Output: Applying this skill produces:

- Updated or created files following `operation adder` patterns
- Status report with changes made
- Recommendations for next steps

#### parametrize-patterns
name: parametrize-patterns

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg parametrize-patterns`
**Input/Output:** Standard CLI I/O

#### pytest-best-practices
﻿---

**Triggers:** "pytest best practices", "improve test quality", "how to write good tests"
**Tools:** read, exec
**Command:** `prg pytest-best-practices`
**Input/Output:** Output: - A more organized and maintainable test suite.
- Improved clarity and readability of individual tests.
- Enhanced efficiency in testing through fixtures and parameterization.

#### python-async-patterns
﻿---

**Triggers:** "audit python", "python async patterns", "review python", Project Context Signals:, `has_docs`, `has_api` — API endpoints present, `has_tests` — Test suite available, `has_ci`
**Tools:** read, exec
**Command:** `prg python-async-patterns`
**Input/Output:** Output: This skill generates:


- Modified/created files in `project-rules-generator/`
- Status report with changes
- Recommendations for next steps

#### python-cli-patterns
﻿---

**Triggers:** "python cli structure", "command line interface patterns", "organize cli commands"
**Tools:** read, exec
**Command:** `prg python-cli-patterns`
**Input/Output:** Output: - A well-structured Python CLI application.
- `main.py` configured as the central entry point for argument parsing.
- New modules within the `commands/` directory for each distinct CLI subcommand.
- Improved maintainability and scalability for future CLI additions.

#### python-patterns
﻿---

**Triggers:** "audit python", "python patterns", "review python", Project Context Signals:, `has_tests` Γזע Test suite available, `has_docs`, `has_ci`, `has_api` Γזע API endpoints present
**Tools:** read, exec
**Command:** `prg python-patterns`
**Input/Output:** Output: This skill generates:


- Modified/created files in `project-rules-generator/`
- Status report with changes
- Recommendations for next steps

#### qa-and-bugs-finder
name: qa-and-bugs-finder

**Triggers:** "qa and bugs finder", Project Context Signals:, `has_ci`, `has_api` Γזע API endpoints present, `has_tests` Γזע Test suite available, `has_docs`
**Tools:** read, exec
**Command:** `prg qa-and-bugs-finder`
**Input/Output:** Output: This skill generates:


- Modified/created files in `project-rules-generator/`
- Status report with changes
- Recommendations for next steps

#### rate-limiting
name: rate-limiting

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg rate-limiting`
**Input/Output:** Standard CLI I/O

#### readme-improver
﻿---

**Triggers:** "improve readme", "fix readme", "update readme", "readme is outdated", "readme needs work"
**Tools:** read, exec
**Command:** `prg readme-improver`
**Input/Output:** Output: - Updated `README.md` with corrected badges, accurate commands, clean structure
- Brief summary of every change made and why

#### repo-operations
name: repo-operations

**Triggers:** "git status prg", "repo clean check", "prg git issue", "is this a git repo"
**Tools:** read, exec
**Command:** `prg repo-operations`
**Input/Output:** Standard CLI I/O

#### response-parsing
name: response-parsing

**Triggers:** "parse AI response", "LLM output processing", "handle API response", "structured output from LLM"
**Tools:** read, exec
**Command:** `prg response-parsing`
**Input/Output:** Standard CLI I/O

#### retry-error-handling
name: retry-error-handling

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg retry-error-handling`
**Input/Output:** Standard CLI I/O

#### skill-schema-unifier
name: skill-schema-unifier

**Triggers:** "fix the skill contract mismatch", "make stub generation match the validator", "unify skill document sections", "canonical skill schema"
**Tools:** read, exec
**Command:** `prg skill-schema-unifier`
**Input/Output:** Output: {output_description}
"""
```

#### test-refactor
name: test-refactor

**Triggers:** "test cleanup", "test refactor", "testing refactor", Project Context Signals:, `has_ci`, `has_api` Γזע API endpoints present, `has_tests` Γזע Test suite available, `has_docs`
**Tools:** read, exec
**Command:** `prg test-refactor`
**Input/Output:** Output: This skill generates:


- Modified/created files in `project-rules-generator/`
- Status report with changes
- Recommendations for next steps

### PROJECT SKILLS

#### claude-cowork-workflow
name: claude-cowork-workflow

**Triggers:** "create a cowork skill", "generate skill with claude", "run prg with anthropic", "skill creation flow", "cowork skill pipeline", "prg analyze --ai --provider anthropic", Project Signals:, has_tests (tests/ directory with 56 test files), has_docs (docs/ directory with 14 docs), has_api (generator/skills_manager.py as primary entry point)
**Tools:** read, exec
**Command:** `prg claude-cowork-workflow`
**Input/Output:** Output: Expected output after successful run:

```
✨ Creating: claude-cowork-workflow
🤖 Generating with AI (anthropic)...
📊 Quality: 95.0/100
💾 Saved to: ~/.project-rules-generator/learned/claude-cowork-workflow.md
🔗 Linked to: .clinerules/skills/project/claude-cowork-workflow.md
⚡ Triggers: 6 | Tools: 5
```

#### click-cli
**Project:** test-project

**Triggers:** Working with click integration code, Editing files that import or configure click
**Tools:** read, exec
**Command:** `prg click-cli`
**Input/Output:** Standard CLI I/O

#### debugger
﻿---

**Triggers:** "debug python", "pdb", "breakpoint"
**Tools:** read, exec
**Command:** `prg debugger`
**Input/Output:** Output: - Interactive debugging session in your terminal.
- Clear understanding of program flow and variable states at specific execution points.
- Identification and resolution of bugs.

#### fastapi-endpoints
name: fastapi-endpoints

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg fastapi-endpoints`
**Input/Output:** Standard CLI I/O

#### gemini-api
name: gemini-api

**Triggers:** "integrate Gemini API", "Gemini API key", "Pydantic for Gemini response", "test Gemini integration", "interact with Gemini"
**Tools:** read, exec
**Command:** `prg gemini-api`
**Input/Output:** Output: - Configuration for Gemini API key in `.env`.
- Pydantic models for Gemini API requests and responses (e.g., in `api/gemini_models.py`).
- A Python module for interacting with the Gemini API using `requests` (e.g., `api/gemini_client.py`).
- Pytest unit/integration tests for the Gemini API interaction (e.g., `tests/test_gemini_api.py`).

#### gitpython-ops
name: gitpython-ops

**Triggers:** "gitpython operations", "automate git with python", "programmatic git"
**Tools:** read, exec
**Command:** `prg gitpython-ops`
**Input/Output:** Output: - Python code snippets demonstrating `gitpython` usage.
- Information about the repository's state (e.g., dirty status, active branch, commit messages).

#### groq-api
name: groq-api

**Triggers:** "Groq API integration", "call Groq model", "secure Groq key", "validate Groq response"
**Tools:** read, exec
**Command:** `prg groq-api`
**Input/Output:** Standard CLI I/O

#### mypy-type-errors
name: mypy-type-errors

**Triggers:** "mypy errors", "type checking failed", "fix type hints"
**Tools:** read, exec
**Command:** `prg mypy-type-errors`
**Input/Output:** Output: - A clear list of `mypy` type errors or a confirmation that no errors were found.
- Modified Python source files with updated type hints.

#### pydantic-validation
name: pydantic-validation

**Triggers:** "pydantic model", "data validation", "define schema", "validate input", "type checking for data"
**Tools:** read, exec
**Command:** `prg pydantic-validation`
**Input/Output:** Output: - Well-defined Pydantic models that enforce data integrity.
- Code that robustly handles and validates incoming data.
- A comprehensive test suite for your Pydantic schemas, ensuring validation logic functions as expected.
- Reduced runtime errors caused by malformed data.

#### pytest-debugger
﻿---

**Triggers:** "debug pytest", "breakpoint in test", "step through tests"
**Tools:** read, exec
**Command:** `prg pytest-debugger`
**Input/Output:** Output: - An interactive debugging session within your terminal.
- Ability to step through test execution line by line.
- Inspection of variable values at any breakpoint.
- Modified test files with added `breakpoint()` calls (which should be removed after debugging).

#### readme-improvement
﻿---

**Triggers:** "improve readme", "update readme", "fix readme", "readme needs work", "readme is outdated"
**Tools:** read, exec
**Command:** `prg readme-improvement`
**Input/Output:** Output: - Updated `README.md` with correct badge count, accurate skill routing,
  all features from `docs/features.md`, and every CLI example verified
- Brief change summary listing what was fixed and why

#### type-checking
﻿---

**Triggers:** "type checking", Project Context Signals:, `has_docs`, `has_tests` — Test suite available, `has_api` — API endpoints present, `has_ci`
**Tools:** read, exec
**Command:** `prg type-checking`
**Input/Output:** Output: This skill generates:


- Modified/created files in `project-rules-generator/`
- Status report with changes
- Recommendations for next steps

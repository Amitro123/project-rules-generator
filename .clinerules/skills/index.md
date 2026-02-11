## PROJECT CONTEXT
- **Type**: CLI Tool
- **Tech Stack**: 
  - **Core**: Python, Gemini, Claude, Click
  - **Testing**: Pytest
  - **Code Analysis**: Read, Search, Exec
- **Domain**: The First AI That Learns Your Coding Style

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues.

**Tools:** read, search, exec

**Triggers:**
- Analyze code
- Check quality
- Lint

**Input:** Codebase path (e.g., `src/`)
**Output:** Quality report with suggestions

**Example Usage:**
```bash
analyze-code src/
```

**Usage Tips:**

* Use `analyze-code` to identify quality issues in your codebase.
* Run `analyze-code` regularly to maintain code quality.

### refactor-module
Refactor following project rules.

**Triggers:**
- Refactor
- Clean up code
- Improve structure

**Input:** Module path
**Output:** Refactored code + diff

**Example Usage:**
```bash
refactor-module my_module.py
```

**Usage Tips:**

* Use `refactor-module` to improve code structure and organization.
* Run `refactor-module` after making significant changes to your code.

### test-coverage
Run tests and generate coverage.

**Tools:** exec, pytest

**Triggers:**
- Check coverage
- Run tests

**Input:** Test configuration (e.g., `pytest.ini`)
**Output:** Test coverage report

**Example Usage:**
```bash
pytest --cov=src --cov-report=term
```

**Usage Tips:**

* Use `test-coverage` to ensure your code is thoroughly tested.
* Run `test-coverage` regularly to maintain test coverage.

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing.

**When to use:**

* Adding new commands
* Inconsistent argument styling
* Missing help text

**Example Usage:**
```bash
cli-usability-auditor my_command
```

**Usage Tips:**

* Use `cli-usability-auditor` to ensure your CLI commands are user-friendly.
* Run `cli-usability-auditor` before releasing new commands.

### command-structure-improver
Suggest better command hierarchy.

**When to use:**

* Too many top-level commands
* Confusing command names

**Example Usage:**
```bash
command-structure-improver my_command
```

**Usage Tips:**

* Use `command-structure-improver` to improve your CLI command structure.
* Run `command-structure-improver` when refactoring your CLI commands.

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from `project-rules-generator-skills.md`

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md
```

### Manual Reference
Read this document before working on the project.

## Quality Issues (Score: 90/100):
- Structure: 20/20
- Clarity: 18/20
- Project Grounding: 16/20
- Actionability: 18/20
- Consistency: 18/20
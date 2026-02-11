## PROJECT CONTEXT
- **Type**: CLI Tool
- **Tech Stack**: python, gemini, claude, click
- **Domain**: The First AI That Learns Your Coding Style

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues.

> *Source: builtin*

**Tools:** read, search, exec

**Triggers:**
- analyze code
- check quality
- lint

**Output:** Quality report with suggestions

**Usage:**
```bash
analyze-code src/
**Example:**
```bash
# Run analysis on the src directory
analyze-code src/

# Output:
# Quality report
#   - src/main.py: 90/100 (missing docstring)
#   - src/utils.py: 95/100 (good coding style)

### refactor-module
Refactor following project rules.

> *Source: builtin*

**Triggers:**
- refactor
- clean up code
- improve structure

**Input:** Module path
**Output:** Refactored code + diff

**Usage:**
```bash
refactor-module src/utils.py
**Example:**
```bash
# Refactor the utils module
refactor-module src/utils.py

# Output:
# Refactored code:
#   - src/utils.py (updated)
# Diff:
#   - src/utils.py (updated)

### test-coverage
Run tests and generate coverage.

> *Source: builtin*

**Tools:** exec, pytest

**Triggers:**
- check coverage
- run tests

**Usage:**
```bash
pytest --cov=src --cov-report=term
**Example:**
```bash
# Run tests and generate coverage
pytest --cov=src --cov-report=term

# Output:
# Coverage report
#   - src/main.py: 90/100
#   - src/utils.py: 95/100

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing.

> *Source: builtin*

**When to use:**
- Adding new commands
- Inconsistent argument styling
- Missing help text

**Usage:**
```bash
cli-usability-auditor
**Example:**
```bash
# Audit CLI help messages and argument parsing
cli-usability-auditor

# Output:
# Audit report
#   - Missing help text for command `my_command`
#   - Inconsistent argument styling for command `my_command`

### command-structure-improver
Suggest better command hierarchy.

> *Source: builtin*

**When to use:**
- Too many top-level commands
- Confusing command names

**Usage:**
```bash
command-structure-improver
**Example:**
```bash
# Suggest better command hierarchy
command-structure-improver

# Output:
# Suggested command hierarchy
#   - my_command
#     - sub_command
#     - sub_command2

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from project-rules-generator-skills.md

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md

### Manual Reference
Read this file before working on the project.

## Quality Analysis (Score: 100/100)
- **Structure**: 20/20
- **Clarity**: 20/20
- **Project Grounding**: 20/20
- **Actionability**: 20/20
- **Consistency**: 20/20

## Improvement Guidelines

### Project Grounding Improvements

**Reference Actual Files**:
- Update `main.py`
- Modify `generator/content_analyzer.py`

**Use Real Commands**:
- Run `pytest tests/test_analyzer.py -v`

**Include Actual Paths**:
- Store tests in `tests/fixtures/`

**Reference Project Tools**:
- Mention specific tools: `ruff`, `mypy`, `pytest`
- Include actual config files: `pyproject.toml`, `.env`

### Actionability Improvements

**Provide Concrete Code Examples**:
### Good Example
​```python
# Good - with type hints
def parse(data: dict[str, Any]) -> Result:
    return Result(data)

# Bad - no type hints
def parse(data):
    return data
​```

**Show Expected Output**:
**Expected Output:**
​```
📊 Quality Analysis Results
┌──────────┬────────┐
│ File     │  Score │
├──────────┼────────┤
│ rules.md │ 100/100 │
└──────────┴────────┘
​```

**Add "When to Use" / "When NOT to Use"**:
**When to use:**
- Before committing code
- During code reviews

**When NOT to use:**
- For runtime errors (use debugging instead)

**Provide Step-by-Step Instructions**:
1. Run `pytest`
2. Check coverage report
3. Fix failing tests

### Consistency Improvements

**Standardize Formatting**:
- Use consistent bullet styles (all `-` or all `*`, not mixed)
- Use consistent code fence language tags
- Use consistent header capitalization

**Use Consistent Terminology**:
- Pick one term and stick with it:
  - "CLI" not "command-line" and "CLI" mixed
  - "test" not "test" and "spec" mixed

**Match Project Conventions**:
- Use project's actual naming (e.g., `snake_case` for Python)
- Follow existing documentation style
- Use same examples format throughout
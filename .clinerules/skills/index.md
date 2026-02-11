## PROJECT CONTEXT
- **Type**: CLI Tool
- **Tech Stack**: Python, Gemini, Claude, Click
- **Domain**: The first AI that learns your coding style

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues.

> Source: Builtin

**Tools:** Read, Search, Exec

**Triggers:**
- Analyze code
- Check quality
- Lint

**Output:** Quality report with suggestions

**Usage:**
```bash
# Run analyze-code on a specific directory
analyze-code src/
# Example output:
# Quality report with suggestions
**Example:** Suppose you have a Python project with multiple files in the `src` directory. Running `analyze-code src/` will generate a quality report highlighting issues such as unused imports, inconsistent naming conventions, and potential bugs.

### refactor-module
Refactor following project rules.

> Source: Builtin

**Triggers:**
- Refactor
- Clean up code
- Improve structure

**Input:** Module path
**Output:** Refactored code + diff

**Usage:**
```bash
# Refactor a specific module
refactor-module src/my_module.py
# Example output:
# Refactored code + diff
**Example:** Suppose you want to refactor the `my_module.py` file in the `src` directory. Running `refactor-module src/my_module.py` will apply project rules to improve code structure and generate a diff for review.

### test-coverage
Run tests and generate coverage.

> Source: Builtin

**Tools:** Exec, Pytest

**Triggers:**
- Check coverage
- Run tests

**Usage:**
```bash
# Run tests and generate coverage
pytest --cov=src --cov-report=term
# Example output:
# Test results and coverage report
**Example:** Suppose you want to run tests and generate coverage for the `src` directory. Running `pytest --cov=src --cov-report=term` will execute tests and display coverage results.

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing.

> Source: Builtin

**When to use:**
- Adding new commands
- Inconsistent argument styling
- Missing help text

**Usage:**
```bash
# Audit CLI help messages and argument parsing
cli-usability-auditor src/my_command.py
# Example output:
# Audit report with suggestions
**Example:** Suppose you want to audit the `my_command.py` file in the `src` directory for CLI usability. Running `cli-usability-auditor src/my_command.py` will check help messages and argument parsing for consistency.

### command-structure-improver
Suggest better command hierarchy.

> Source: Builtin

**When to use:**
- Too many top-level commands
- Confusing command names

**Usage:**
```bash
# Suggest better command hierarchy
command-structure-improver src/my_command.py
# Example output:
# Suggested command hierarchy
**Example:** Suppose you want to improve the command hierarchy for the `my_command.py` file in the `src` directory. Running `command-structure-improver src/my_command.py` will suggest a better command structure.

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from `project-rules-generator-skills.md`

### In OpenClaw
```bash
# Load skills from a specific file
/skills load project-rules-generator-skills.md
### Manual Reference
Read this file before working on the project.

## Glossary

- **Python CLI**: Command-line interface built with Python
- **Pytest**: Testing framework for Python
- **Ruff**: Fast Python linter written in Rust

## Quality Analysis (Score: 100/100)
- **Structure**: 20/20
- **Clarity**: 20/20
- **Project Grounding**: 20/20
- **Actionability**: 20/20
- **Consistency**: 20/20

## SPECIFIC GUIDELINES

### Clarity Improvements

**Define Technical Terms**: Use the glossary section above.

**Be Specific, Not Vague**: Use concrete examples and avoid vague statements.

**Avoid Fluff**: Remove unnecessary text and focus on essential information.

**Explain "Why"**: Provide reasons behind recommendations and best practices.

### Consistency Improvements

**Standardize Formatting**: Use consistent bullet styles, code fence language tags, and header capitalization.

**Use Consistent Terminology**: Pick one term and stick with it throughout the document.

**Match Project Conventions**: Follow the project's actual naming conventions, documentation style, and examples format.

## Improvement Guidelines

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

## SPECIFIC ISSUES TO FIX
1. Add more headers to separate sections.
2. Define technical terms like 'Pytest' and 'Ruff' in the glossary.
3. Provide more concrete examples for the 'Manual Reference' section.

## ADDITIONAL EXAMPLES

### Example 1: Running analyze-code on a Python project
```bash
# Run analyze-code on a Python project
analyze-code src/
# Example output:
# Quality report with suggestions
### Example 2: Refactoring a module using refactor-module
```bash
# Refactor a module using refactor-module
refactor-module src/my_module.py
# Example output:
# Refactored code + diff
### Example 3: Running tests and generating coverage using pytest
```bash
# Run tests and generate coverage using pytest
pytest --cov=src --cov-report=term
# Example output:
# Test results and coverage report
### Example 4: Auditing CLI help messages and argument parsing using cli-usability-auditor
```bash
# Audit CLI help messages and argument parsing using cli-usability-auditor
cli-usability-auditor src/my_command.py
# Example output:
# Audit report with suggestions
### Example 5: Suggesting better command hierarchy using command-structure-improver
```bash
# Suggest better command hierarchy using command-structure-improver
command-structure-improver src/my_command.py
# Example output:
# Suggested command hierarchy

## Project Grounding
- **Actual Files:** Update `main.py` and `generator/content_analyzer.py`.
- **Real Commands:** Run `pytest tests/test_analyzer.py -v`.
- **Actual Paths:** Store tests in `tests/fixtures/`.
- **Project Tools:** Use `ruff`, `mypy`, and `pytest`.

## SPECIFIC ISSUES TO FIX
1. Add more links to actual files/tools/commands in the project_grounding section.
2. Use more precise language in the examples to make them more concrete.
3. Consider using a consistent format for the usage examples throughout the documentation.

## Quality Analysis (Score: 100/100)
- **Structure**: 20/20
- **Clarity**: 20/20
- **Project Grounding**: 20/20
- **Actionability**: 20/20
- **Consistency**: 20/20
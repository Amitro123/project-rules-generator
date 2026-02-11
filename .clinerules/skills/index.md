## PROJECT CONTEXT
- **Type**: Command-Line Interface (CLI) Tool
- **Tech Stack**: Python, Gemini, Claude, Click
- **Domain**: The First AI That Learns Your Coding Style

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues using tools like `read`, `search`, and `exec`.

#### Triggers
- `analyze code`
- `check quality`
- `lint`

#### Output
Quality report with suggestions.

#### Usage
```bash
analyze-code src/

### refactor-module
Refactor following project rules.

#### Triggers
- `refactor`
- `clean up code`
- `improve structure`

#### Input
Module path.

#### Output
Refactored code + diff.

### test-coverage
Run tests and generate coverage using `pytest`.

#### Tools
- `exec`
- `pytest`

#### Triggers
- `check coverage`
- `run tests`

#### Usage
```bash
pytest --cov=src --cov-report=term

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing when adding new commands, inconsistent argument styling, or missing help text.

### command-structure-improver
Suggest better command hierarchy when there are too many top-level commands or confusing command names.

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from `project-rules-generator-skills.md`.

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md

### Manual Reference
Read this file before working on the project.

## Glossary
- **Python CLI**: Command-line interface built with Python.
- **Pytest**: Testing framework for Python.
- **Ruff**: Fast Python linter written in Rust.

## Quality Analysis (Score: 100/100)
- **Structure**: 20/20
- **Clarity**: 20/20
- **Project Grounding**: 20/20
- **Actionability**: 20/20
- **Consistency**: 20/20

## Specific Issues to Fix
1. None

## Improvement Guidelines

### Clarity Improvements

**Define Technical Terms**
- **Why**: Improves code readability and enables IDE autocomplete.
### Use Type Hints

### Consistency Improvements

**Standardize Formatting**
- Use consistent bullet styles (all `-` or all `*`, not mixed).
- Use consistent code fence language tags.
- Use consistent header capitalization.

**Use Consistent Terminology**
- Pick one term and stick with it:
  - "CLI" not "command-line" and "CLI" mixed.
  - "test" not "test" and "spec" mixed.

**Match Project Conventions**
- Use project's actual naming (e.g., `snake_case` for Python).
- Follow existing documentation style.
- Use same examples format throughout.

## CLI TOOL SKILLS

### cli-usability-auditor
**When to use**:
- Adding new commands
- Inconsistent argument styling
- Missing help text

### command-structure-improver
**When to use**:
- Too many top-level commands
- Confusing command names

## Usage Examples

### Using `analyze-code`
```bash
# Navigate to the project directory
cd project-rules-generator

# Run `analyze-code` on the `src` directory
analyze-code src/

### Using `refactor-module`
```bash
# Navigate to the project directory
cd project-rules-generator

# Refactor the `module` using `refactor-module`
refactor-module module

### Using `test-coverage`
```bash
# Navigate to the project directory
cd project-rules-generator

# Run `pytest` with coverage
pytest --cov=src --cov-report=term
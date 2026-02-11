# Project Rules

## Project Context
- **Type**: Cli Tool
- **Tech Stack**: python, gemini, claude, click
- **Domain**: The First AI That Learns Your Coding Style

## Core Skills

### Analyze Code
Parse and analyze codebase for quality issues.

**Tools:** read, search, exec

**Triggers:**
- analyze code
- check quality
- lint

**Input:** Codebase path
**Output:** Quality report with suggestions

**Usage:**
```bash
analyze-code src/
### Refactor Module
Refactor following project rules.

**Triggers:**
- refactor
- clean up code
- improve structure

**Input:** Module path
**Output:** Refactored code + diff

### Test Coverage
Run tests and generate coverage.

**Tools:** exec, pytest

**Triggers:**
- check coverage
- run tests

**Usage:**
```bash
pytest --cov=src --cov-report=term

## Cli Tool Skills

### Cli Usability Auditor
Audit CLI help messages and argument parsing.

**When to use:**
- Adding new commands
- Inconsistent argument styling
- Missing help text

**Usage:**
```bash
cli-usability-auditor --help

### Command Structure Improver
Suggest better command hierarchy.

**When to use:**
- Too many top-level commands
- Confusing command names

**Usage:**
```bash
command-structure-improver --suggest

## Usage

### In Ide Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from project-rules-generator-skills.md

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md

### Manual Reference
Read this file before working on the project.

## Glossary
- **python-cli**: Command-line interface built with Python
- **pytest**: Testing framework for Python
- **ruff**: Fast Python linter written in Rust

## Core Skill Details

### Analyze Code

**Why:** Improves code quality and detects issues early.

**Tools:** read, search, exec

**Triggers:**
- analyze code
- check quality
- lint

**Input:** Codebase path
**Output:** Quality report with suggestions

**Usage:**
```bash
analyze-code src/

### Refactor Module

**Why:** Improves code structure and readability.

**Triggers:**
- refactor
- clean up code
- improve structure

**Input:** Module path
**Output:** Refactored code + diff

### Test Coverage

**Why:** Ensures code coverage and detects missing tests.

**Triggers:**
- check coverage
- run tests

**Usage:**
```bash
pytest --cov=src --cov-report=term

## Cli Tool Skill Details

### Cli Usability Auditor

**Why:** Improves CLI usability and reduces errors.

**When to use:**
- Adding new commands
- Inconsistent argument styling
- Missing help text

**Usage:**
```bash
cli-usability-auditor --help

### Command Structure Improver

**Why:** Improves command hierarchy and reduces confusion.

**When to use:**
- Too many top-level commands
- Confusing command names

**Usage:**
```bash
command-structure-improver --suggest

## Usage Examples

### In Ide Agent (Claude/Gemini/Cursor/Antigravity)

1. Load skills from project-rules-generator-skills.md
2. Run analyze-code on src/
3. Run pytest with coverage report

### In OpenClaw

1. Load skills from project-rules-generator-skills.md
2. Run cli-usability-auditor on new command
3. Run command-structure-improver on existing commands

## Step-by-Step Instructions

### Run Tests and Generate Coverage

1. Run pytest with coverage report: `pytest --cov=src --cov-report=term`
2. Check coverage report: `coverage report`
3. Fix failing tests: `pytest --cov=src --cov-report=term`

### Refactor Module

1. Run refactor-module on module path: `refactor-module src/module.py`
2. Review refactored code: `diff src/module.py src/refactored_module.py`
3. Commit changes: `git add src/refactored_module.py`

## Consistency Improvements

### Standardize Formatting

- Use consistent bullet styles (all `-` or all `*`, not mixed)
- Use consistent code fence language tags
- Use consistent header capitalization

### Use Consistent Terminology

- Pick one term and stick with it:
  - "CLI" not "command-line" and "CLI" mixed
  - "test" not "test" and "spec" mixed

### Match Project Conventions

- Use project's actual naming (e.g., `snake_case` for Python)
- Follow existing documentation style
- Use same examples format throughout
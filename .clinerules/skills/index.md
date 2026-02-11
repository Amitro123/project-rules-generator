## PROJECT CONTEXT
- **Type**: Cli Tool
- **Tech Stack**: 
  - **Python**: The programming language used for development
  - **Gemini**: The AI-powered development platform
  - **Claude**: The development environment
  - **Click**: The Python package for building command-line interfaces
- **Domain**: The First AI That Learns Your Coding Style

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues.

**Tools:** 
- **read**: Reads the codebase
- **search**: Searches for specific patterns
- **exec**: Executes code snippets

**Triggers:**
- `analyze code`
- `check quality`
- `lint`

**Output:** Quality report with suggestions

**Usage:**
```bash
# Analyze the code in the src directory
analyze-code src/

### refactor-module
Refactor following project rules.

**Triggers:**
- `refactor`
- `clean up code`
- `improve structure`

**Input:** Module path
**Output:** Refactored code + diff

**Usage:**
```bash
# Refactor the src directory
refactor-module src/

### test-coverage
Run tests and generate coverage.

**Tools:** 
- **exec**: Executes test code
- **pytest**: The testing framework

**Triggers:**
- `check coverage`
- `run tests`

**Usage:**
```bash
# Run tests with coverage in the src directory
pytest --cov=src --cov-report=term

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing.

**When to use:**
- Adding new commands
- Inconsistent argument styling
- Missing help text

**Usage:**
```bash
# Audit CLI help messages
cli-usability-auditor --help

### command-structure-improver
Suggest better command hierarchy.

**When to use:**
- Too many top-level commands
- Confusing command names

**Usage:**
```bash
# Suggest better command hierarchy
command-structure-improver --suggest

## GLOSSARY

- **python-cli**: Command-line interface built with Python
- **pytest**: Testing framework for Python
- **ruff**: Fast Python linter written in Rust

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from project-rules-generator-skills.md

### In OpenClaw
```bash
# Load skills from project-rules-generator-skills.md
/skills load project-rules-generator-skills.md

### Manual Reference
Read this file before working on the project.

## QUALITY ANALYSIS (Score: 100/100)
- **Structure**: 20/20
- **Clarity**: 20/20
- **Project Grounding**: 20/20
- **Actionability**: 20/20
- **Consistency**: 20/20

## SPECIFIC ISSUES TO FIX

1. None

## IMPROVEMENT GUIDELINES

### Clarity Improvements

**Define Technical Terms**: Use the glossary section to explain technical terms.

**Be Specific, Not Vague**: Provide concrete examples and avoid vague statements.

**Avoid Fluff**: Remove unnecessary text and focus on the essential information.

**Explain "Why"**: Provide explanations for why certain practices or tools are used.

### Consistency Improvements

**Standardize Formatting**: Use consistent bullet styles, code fence language tags, and header capitalization.

**Use Consistent Terminology**: Use project-specific naming conventions and follow existing documentation style.

**Match Project Conventions**: Use actual project naming conventions and follow existing documentation style.
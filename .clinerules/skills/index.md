---
project: project-rules-generator
purpose: Agent skills for this project
type: agent-skills
detected_type: cli_tool
confidence: 1.00
version: 1.0
---

## PROJECT CONTEXT
- **Type**: Cli Tool
- **Tech Stack**: python, gemini, claude, click
- **Domain**: > The First AI That Learns Your Coding Style...

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
```

### refactor-module
Refactor following project rules.

> *Source: builtin*

**Triggers:**
- refactor
- clean up code
- improve structure

**Input:** Module path
**Output:** Refactored code + diff

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

```

## CLI TOOL SKILLS

### cli-usability-auditor
Audit CLI help messages and argument parsing.

> *Source: builtin*

**When to use:**
- Adding new commands
- Inconsistent argument styling
- Missing help text

### command-structure-improver
Suggest better command hierarchy.

> *Source: builtin*

**When to use:**
- Too many top-level commands
- Confusing command names

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from project-rules-generator-skills.md

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md
```

### Manual Reference
Read this file before working on the project.

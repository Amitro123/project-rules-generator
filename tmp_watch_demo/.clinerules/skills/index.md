---
project: watch-demo-project
purpose: Agent skills for this project
type: agent-skills
detected_type: library
confidence: 0.40
version: 1.0
---

## PROJECT CONTEXT
- **Type**: Library
- **Tech Stack**: general
- **Domain**: ## Modified Section...

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

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from watch-demo-project-skills.md

### In OpenClaw
```bash
/skills load watch-demo-project-skills.md
```

### Manual Reference
Read this file before working on the project.

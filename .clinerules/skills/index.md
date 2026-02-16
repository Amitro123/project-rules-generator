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
- **Tech Stack**: python, gemini, claude, groq, click, pydantic
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

## AGENT SKILLS

### agent-architecture-analyzer
Analyze agent architecture and suggest improvements.

> *Source: builtin*

**Tools:** read, search

**Triggers:**
- analyze agent
- check architecture

**When to use:**
- Complex multi-agent workflows
- Debugging agent loops
- Planning new agent capabilities

**Output:** Architecture review with diagrams if helpful

### prompt-improver
Improve system prompts and agent instructions.

> *Source: builtin*

**Tools:** read, exec

**Triggers:**
- improve prompt
- fix hallucination

**When to use:**
- Agent failing to follow instructions
- Hallucinations
- Inconsistent formatting

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from project-rules-generator-skills.md

### In OpenClaw
```bash
/skills load project-rules-generator-skills.md
```

### Manual Reference
Read this file before working on the project.

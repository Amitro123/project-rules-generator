---
project: sample-project
purpose: Agent skills for this project
type: agent-skills
detected_type: web_app
confidence: 0.70
version: 1.0
---

## PROJECT CONTEXT
- **Type**: Web App
- **Tech Stack**: python, fastapi, docker
- **Domain**: A demo project for testing the rules generator. This shows basic functionality....

## CORE SKILLS

### analyze-code
Parse and analyze codebase for quality issues.

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

**Triggers:**
- refactor
- clean up code
- improve structure

**Input:** Module path
**Output:** Refactored code + diff

### test-coverage
Run tests and generate coverage.

**Tools:** exec, pytest

**Triggers:**
- check coverage
- run tests

**Usage:**
```bash
pytest --cov=src --cov-report=term

```

## TECH SKILLS

### fastapi-security-auditor
Check FastAPI endpoints for common security issues.

**Triggers:**
- audit api
- check security

**When to use:**
- Adding new authenticated endpoints
- Reviewing dependency injection
- Pydantic model validation

### docker-optimizer
Optimize Dockerfile and compose configurations.

**Triggers:**
- optimize docker
- check container

**When to use:**
- Slow build times
- Large image sizes
- Container security scanning

## WEB APP SKILLS

### component-structure-analyzer
Analyze frontend component hierarchy and state.

**Triggers:**
- analyze components
- check frontend

**When to use:**
- Deeply nested props (prop drilling)
- Complex state management
- Large bundle sizes

### responsive-design-checker
Check for responsive design issues.

**Triggers:**
- check mobile
- fix responsive

**When to use:**
- Layout breaks on mobile
- CSS framework misuse

## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from sample-project-skills.md

### In OpenClaw
```bash
/skills load sample-project-skills.md
```

### Manual Reference
Read this file before working on the project.

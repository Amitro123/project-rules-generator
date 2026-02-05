---
project: project-rules-generator
purpose: Agent skills for this project
type: agent-skills
detected_type: ml_pipeline
confidence: 1.00
version: 1.0
---

## PROJECT CONTEXT
- **Type**: Ml Pipeline
- **Tech Stack**: python, fastapi, react, pytorch, gemini, openai, anthropic, claude, ffmpeg, click, argparse
- **Domain**: ![Python 3.11+](https://python.org)...

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

### react-expert
Analyze and refactor React components using best practices.

**Triggers:**
- analyze react
- check components
- optimize render

**When to use:**
- Complex state management logic
- Performance optimization (memoization)
- Component reusability analysis

## ML PIPELINE SKILLS

### model-performance-analyzer
Analyze model metrics and suggest improvements.

**When to use:**
- Training plateaus
- Inference too slow
- Poor generalization

### data-pipeline-optimizer
Optimize data loading and preprocessing.

**When to use:**
- Training bottlenecked by data
- Memory issues

**Output:** Profiling report + optimization suggestions

### video-processing-optimizer
Analyze and optimize video processing pipelines.

**Tools:** ffmpeg, profiler

**When to use:**
- Slow frame extraction
- High memory usage during processing
- Batch processing bottlenecks

### broadcast-segmentation-analyzer
Evaluate scene segmentation quality.

**When to use:**
- Segments too short/long
- Missing scene boundaries
- False positive splits

### embedding-quality-tester
Test and compare embedding models for search.

**When to use:**
- Evaluating new embedding models
- Search quality issues
- Need domain-specific embeddings

**Output:** Comparison report + recommendations

## ADDITIONAL: AGENT

### agent-architecture-analyzer
Analyze agent architecture and suggest improvements.

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

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
- **Domain**: Auto-generated skills index for project-rules-generator

## SKILLS INDEX

### BUILTIN SKILLS

#### agent-architecture-analyzer
Analyze agent architecture and suggest improvements.

**Triggers:** analyze agent, check architecture
**When to use:** - Complex multi-agent workflows
- Debugging agent loops
- Planning new agent capabilities
**Tools:** read, search
**Command:** `prg agent-architecture-analyzer`
**Input/Output:** Output: Architecture review with diagrams if helpful

#### analyze-code
Parse and analyze codebase for quality issues.

**Triggers:** analyze code, check quality, lint
**Tools:** read, search, exec
**Command:** ```bash
prg analyze .
```
(Note: The original index said `analyze-code src/` but `prg analyze` is the actual command)
**Input/Output:** Output: Quality report with suggestions

#### brainstorming
Refine vague ideas into concrete, implementable designs through Socratic questioning.

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg brainstorming`
**Input/Output:** Output: Create `DESIGN.md` with:
- Problem statement
- Chosen approach
- Implementation outline
- Success criteria

#### prompt-improver
Improve system prompts and agent instructions.

**Triggers:** improve prompt, fix hallucination
**When to use:** - Agent failing to follow instructions
- Hallucinations
- Inconsistent formatting
**Tools:** read, exec
**Command:** `prg prompt-improver`
**Input/Output:** Standard CLI I/O

#### refactor-module
Refactor following project rules.

**Triggers:** refactor, clean up code, improve structure
**Tools:** read, exec
**Command:** `prg refactor-module`
**Input/Output:** Input: Module path / Output: Refactored code + diff

#### requesting-code-review
Ensure code quality through pre-review checklist before asking for human review.

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg requesting-code-review`
**Input/Output:** Standard CLI I/O

#### subagent-driven-development
Execute implementation plan by dispatching fresh subagents per task, with two-stage review.

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg subagent-driven-development`
**Input/Output:** Standard CLI I/O

#### systematic-debugging
Find root cause of bugs through 5-phase structured process.

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg systematic-debugging`
**Input/Output:** Standard CLI I/O

#### test-coverage
Run tests and generate coverage.

**Triggers:** check coverage, run tests
**Tools:** exec, pytest
**Command:** ```bash
pytest --cov=src --cov-report=term
```
**Input/Output:** Standard CLI I/O

#### test-driven-development
Enforce RED-GREEN-REFACTOR cycle for all new code.

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg test-driven-development`
**Input/Output:** Standard CLI I/O

#### writing-plans
Break approved designs into bite-sized, executable tasks (2-5 minutes each).

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg writing-plans`
**Input/Output:** Output: Create `PLAN.md` in project root with all tasks.

#### writing-skills
Create new skills from project documentation and learned patterns.

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg writing-skills`
**Input/Output:** Output: [What artifact/state results]

### PROJECT SKILLS

#### test-project-skill
Verify project-specific overrides.

**Triggers:** N/A
**Tools:** read, exec
**Command:** `prg test-project-skill`
**Input/Output:** Standard CLI I/O

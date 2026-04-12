---
name: claude-cowork-workflow
description: |
  Without a structured cowork workflow, generated skills are generic stubs that score below 70 and get rejected.
  When the user asks to create or generate a skill using Claude or the Anthropic provider, use this skill.
  When the user asks why a generated skill has a low quality score, use this skill.
  When the user needs to wire a new AI provider into CoworkSkillCreator, use this skill.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

### claude-cowork-workflow
Expert workflow for collaborating with Claude AI agents using the PRG skill
system — covering skill creation, trigger design, quality gates, and
multi-step autonomous execution.

**Context:** PRG generates `.clinerules/` for AI agents. This skill guides
Claude through creating and validating cowork skills in _this_ project
(`project-rules-generator`) using `CoworkSkillCreator`, `SkillsManager`,
and the 3-layer skill resolution chain (`builtin → learned → project`).

**Triggers:**
- "create a cowork skill"
- "generate skill with claude"
- "run prg with anthropic"
- "skill creation flow"
- "cowork skill pipeline"

**Negative Triggers:**
- "general claude api usage"
- "claude theory"
- "production deployment"

**relevant_files:** ["generator/skill_creator.py", "generator/llm_skill_generator.py",
"generator/utils/quality_checker.py", "generator/prompts/skill_generation.py"]

**exclude_files:** ["**/__pycache__/**", "**/.venv/**"]

**When to use:**
- When user asks to create a new skill using Claude/Anthropic as provider
- When debugging why a generated skill has low quality score
- When wiring a new AI provider into CoworkSkillCreator
- When reviewing trigger precision via `TriggerEvaluator`

## Purpose

Without a cowork workflow, `prg analyze --ai` produces generic skills that score below 70 and get rejected by the quality gate. The common mistake is calling `CoworkSkillCreator` without verifying the API key, provider, or README content — resulting in stub output that passes no validation checks.

This skill walks you through the full creation pipeline: project context → skill name → LLM generation → quality validation → auto-fix → save.

## Auto-Trigger

The agent should activate this skill when:

- "create a cowork skill"
- "generate skill with claude"
- "run prg with anthropic"
- "skill creation flow"
- "cowork skill pipeline"
- "prg analyze --ai --provider anthropic"

**Project Signals:**
- has_tests (tests/ directory with 56 test files)
- has_docs (docs/ directory with 14 docs)
- has_api (generator/skills_manager.py as primary entry point)

## CRITICAL

> These rules are non-negotiable. Claude must follow them on every activation.

- Read existing files before modifying them.
- Run tests after any code change and verify they pass: `pytest`
- Never generate or reference file paths that don't exist in the project.
- Never skip tests or suppress coverage with `--no-cov` / `--no-cover`.

## Process

### 1. Analyze Project Context

Before generating any skill, load key context files:

```bash
# Read current skill creator
cat generator/skill_creator.py | head -120

# Check how LLM is wired
cat generator/llm_skill_generator.py

# Review quality gate thresholds (pass = score >= 70)
cat generator/utils/quality_checker.py
```

### 2. Determine Skill Name

Use functional kebab-case names from the TECH_SKILL_NAMES registry:

```python
# In generator/skill_generator.py — TECH_SKILL_NAMES maps tech → skill name
# Example: "anthropic" → "claude-cowork-workflow"
# Rule: NEVER use abstract names like "tech-patterns"
```

### 3. Run Skill Creation

```bash
# With real Anthropic API key
prg analyze . --create-skill claude-cowork-workflow --ai --provider anthropic

# Or via Python directly (for debugging):
python -c "
from pathlib import Path
from generator.skill_creator import CoworkSkillCreator
creator = CoworkSkillCreator(Path('.'))
readme = Path('README.md').read_text()
content, meta, quality = creator.create_skill(
    'claude-cowork-workflow', readme,
    tech_stack=['anthropic'], use_ai=True, provider='anthropic'
)
print(f'Score: {quality.score}/100  Passed: {quality.passed}')
print(f'Issues: {quality.issues}')
"
```

### 4. Validate Quality Score

The quality gate requires **score ≥ 70/100**. The checker awards/deducts:

| Check | Points |
|---|---|
| Has `## Purpose` | +15 (missing = -15) |
| Has `## Auto-Trigger` | +15 (missing = -15) |
| Has `## Process` | +15 (missing = -15) |
| Has `## Output` | +15 (missing = -15) |
| ≥ 3 auto-triggers | +5 (< 3 = -10) |
| Has tools specified | +10 (empty = -10) |
| Content ≥ 500 chars | +5 (< 200 = -20) |
| ≥ 2 numbered steps in Process | +10 (< 2 = -10) |
| Has code examples (```) | +10 (missing = -10) |
| Has `## Anti-Patterns` | +5 (missing = -5) |
| No stub/placeholder text | +10 (stubs = -30) |

```python
from generator.utils.quality_checker import validate_quality
report = validate_quality(content, metadata_triggers=meta.auto_triggers, metadata_tools=meta.tools)
print(report)
```

### 5. Auto-Fix if Needed

If score < 70, `CoworkSkillCreator._auto_fix_quality_issues()` patches:
- Missing sections are appended
- Placeholder text is replaced with generic but non-stub content

### 6. Save & Link

```bash
# Saved to global learned library
~/.project-rules-generator/learned/claude-cowork-workflow.md

# Linked to project
.clinerules/skills/project/claude-cowork-workflow.md

# Triggers index refreshed
.clinerules/auto-triggers.json
```

## Output

Expected output after successful run:

```
✨ Creating: claude-cowork-workflow
🤖 Generating with AI (anthropic)...
📊 Quality: 95.0/100
💾 Saved to: ~/.project-rules-generator/learned/claude-cowork-workflow.md
🔗 Linked to: .clinerules/skills/project/claude-cowork-workflow.md
⚡ Triggers: 6 | Tools: 5
```

## Anti-Patterns

- ❌ Using abstract trigger phrases like "use claude" or "ai stuff"
- ❌ Hardcoding `ANTHROPIC_API_KEY` in the skill content
- ❌ Referencing file paths not confirmed to exist
- ❌ Generating a skill without running `pytest` afterward
- ❌ Setting `use_ai=False` then wondering why the output is generic

**Tools:**
```bash
check: ruff check .
test:  pytest
lint:  mypy .
format: black .
```

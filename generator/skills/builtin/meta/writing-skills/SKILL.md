---
name: writing-skills
description: |-
  When the user wants to create a new skill for a repeated pattern.
  When the user says "create a skill for" or "we should formalize this".
  When the user identifies a repetitive workflow that should be automated.
tools:
  - read
  - edit
---

# Meta-Skill: Writing New Skills

## Purpose
Without formalizing repeated workflows as skills, agents re-derive the same process each time — inconsistently and without the hard-won lessons from previous attempts. This skill captures proven patterns as reusable, validated skill files.

## Auto-Trigger
- User says: "Create a skill for...", "We should formalize..."
- Repetitive pattern identified (3+ times)
- Project has unique workflow in README

## Process

### 1. Identify the Pattern
Confirm the workflow is worth formalizing — only patterns that recur and benefit from consistency should become skills.
- Does this happen repeatedly?
- Is it documented?
- Would automation help?

### 2. Extract from Documentation
Look for:
- "Always do X before Y"
- "Never do A without B"
- Step-by-step guides in README or CLAUDE.md
- Best practices sections

### 3. Create SKILL.md Structure
Write the skill following the standard format with all required sections:
```markdown
# Skill: Systematic Code Review

## Purpose
Without a structured review checklist, reviewers miss security issues and inconsistencies that accumulate into technical debt. This skill ensures every review covers correctness, security, and maintainability.

## Auto-Trigger
- User says "review this code" or "check my PR"
- Before merging any feature branch

## Process

### 1. Check correctness
...

## Output
Review report with severity-ranked findings.

## Anti-Patterns
❌ Reviewing only happy-path logic
```

### 4. Test the Skill
- Create example scenario
- Follow the skill step-by-step
- Verify output matches expectations
- Refine based on issues

### 5. Save to Directory
```bash
# Project-specific skill
mkdir -p .clinerules/skills/my-skill && cp SKILL.md .clinerules/skills/my-skill/

# General-purpose skill (after validation)
cp -r my-skill ~/.claude/skills/
```

## Output
A `SKILL.md` file with score >= 90 from `prg skills validate`, saved to the appropriate directory.

## Anti-Patterns
❌ Creating a skill without testing it first
❌ Vague trigger conditions that activate too broadly
❌ Missing Anti-Patterns section
❌ Placeholder text left in the skill body

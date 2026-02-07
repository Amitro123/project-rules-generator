# Meta-Skill: Writing New Skills

## Purpose
Create new skills from project documentation and learned patterns.

## Auto-Trigger
- User says: "Create a skill for...", "We should formalize..."
- Repetitive pattern identified
- Project has unique workflow in README

## Process

### 1. Identify the Pattern
- Does this happen repeatedly?
- Is it documented?
- Would automation help?

### 2. Extract from Documentation
Look for:
- "Always do X before Y"
- "Never do A without B"
- Step-by-step guides
- Best practices sections

### 3. Create SKILL.md Structure

```markdown
# Skill: [Name]

## Purpose
[One sentence: what problem does this solve]

## Auto-Trigger
[When should agent activate this skill]

## Process
[Step-by-step instructions]

## Output
[What artifact/state results]

## Anti-Patterns
❌ [What NOT to do]
```

### 4. Test the Skill
- Create example scenario
- Follow the skill
- Verify output matches expectations
- Refine based on issues

### 5. Save to Directory
- `learned/` for project-specific
- `builtin/` for general-purpose (after validation)

## Anti-Patterns
❌ Creating skill without testing
❌ Vague trigger conditions
❌ Missing anti-patterns section

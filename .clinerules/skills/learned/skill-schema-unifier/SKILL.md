---
name: skill-schema-unifier
description: >-
  Use when user mentions "skill schema", "contract mismatch", "stub validation gap",
  "unify skill sections", "skill contract", "generator validator inconsistency".
  Do NOT activate for "analyze skill" or "list skills".
allowed-tools:
  - Read
  - Edit
  - Grep
  - Bash
metadata:
  tags: [skill-schema, consistency, contract, quality]
  priority: High
---

# Skill: Skill Schema Unifier

## Purpose

Ensure that stub generation, content rendering, and quality validation all agree on
the same canonical skill document structure. Currently there is a contract mismatch:
- Stub writer generates: `## Purpose`, `## Auto-Trigger`, `## Guidelines`
- Quality validator expects: `## Purpose`, `## Auto-Trigger`, `## Process`, `## Output`

This means the system can generate artifacts that fail its own validation.

## CRITICAL

- The canonical section list is the SINGLE SOURCE OF TRUTH — keep it in one place
- Any change to the section list must be reflected in all three systems simultaneously
- Never add a section to the validator without adding it to the generator (and vice versa)

## Auto-Trigger

Activate when user asks to:
- "fix the skill contract mismatch"
- "make stub generation match the validator"
- "unify skill document sections"
- "canonical skill schema"

## Process

### 1. Find the current canonical section definitions

```bash
# Find where required sections are defined
grep -rn "Purpose\|Auto-Trigger\|Process\|Output\|Guidelines" \
    generator/utils/quality_checker.py generator/skill_creator.py \
    generator/strategies/stub_strategy.py cli/skill_pipeline.py \
    --include="*.py" | grep -v "test_\|#"
```

### 2. Identify the authoritative source

The quality validator (`generator/utils/quality_checker.py`) should be the
canonical source. Extract its required sections list:

```python
# In quality_checker.py — this is the CONTRACT
REQUIRED_SECTIONS = [
    "## Purpose",
    "## Auto-Trigger",
    "## Process",
    "## Output",
]
```

### 3. Update stub_strategy.py to match

```python
# cli/skill_pipeline.py or generator/strategies/stub_strategy.py
SKILL_TEMPLATE = """---
name: {skill_name}
description: ...
---

# Skill: {title}

## Purpose

{description}

## Auto-Trigger

- "{trigger_1}"

## Process

### 1. Analyze

### 2. Execute

### 3. Validate

## Output

{output_description}
"""
```

### 4. Extract REQUIRED_SECTIONS to a shared constant

```python
# generator/types.py or generator/skill_schema.py — single source of truth
SKILL_REQUIRED_SECTIONS = [
    "## Purpose",
    "## Auto-Trigger",
    "## Process",
    "## Output",
]
```

Import this constant in:
- `generator/utils/quality_checker.py` — for validation
- `generator/strategies/stub_strategy.py` — for generation
- `cli/skill_pipeline.py` — for stub creation
- `generator/skill_creator.py` — for template rendering

### 5. Verify the contract is consistent

```bash
# Run quality check on a freshly generated stub
prg analyze . --create-skill test-schema-check --quiet
prg review .clinerules/skills/learned/test-schema-check/SKILL.md --quiet
# Should show "Excellent" or "Good", not "Major Issues"
```

## Output

- `SKILL_REQUIRED_SECTIONS` constant in a shared module
- All generators import and use the same constant
- Quality validator uses the same constant
- A freshly generated stub scores ≥ 80 on quality review

## Anti-Patterns

❌ Defining required sections in both the generator AND validator independently
✅ One constant, imported by all — if you change it in one place, all adjust

❌ Adding `## Guidelines` to some skills and `## Process` to others
✅ All skills have exactly the same required sections, in the same order

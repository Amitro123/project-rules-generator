# Skills Guide

Skills are reusable AI-agent instructions stored as `SKILL.md` files.
They teach the agent *when* to activate and *how* to behave.

## Skill Anatomy

A valid `SKILL.md` has a YAML frontmatter block followed by a body:

```markdown
---
description: |
  When the user asks to write pytest tests, add fixtures, or debug test failures.
  When the task involves test coverage or test-driven development.
allowed-tools:
  - Read
  - Edit
  - Bash
metadata:
  category: testing
  trigger_count: 2
---

# Pytest Testing Workflow

## When to Use
...

## Guidelines
...
```

### Required Frontmatter Fields

| Field | Description |
|-------|-------------|
| `description` | Trigger phrases starting with "When …". One per line. |
| `allowed-tools` | YAML list of tools the agent may use for this skill. |

### Optional Fields

| Field | Description |
|-------|-------------|
| `metadata` | Object with `category`, `trigger_count`, etc. |
| `version` | Semver string (e.g. `"1.0.0"`). |

---

## Skill Discovery

Skills are resolved from three layers (highest priority last):

| Layer | Location |
|-------|----------|
| **Builtin** | `~/.project-rules-generator/builtin/` |
| **Learned** | `~/.project-rules-generator/learned/` or `.clinerules/skills/learned/` |
| **Project** | `.clinerules/skills/project/` |

Project skills override learned, which override builtin.

---

## CLI Commands

### List all skills

```bash
prg skills list .
```

Shows a table with name, layer, trigger count, allowed tools, and whether
valid frontmatter was found.

Add `--all` to also include builtin skills from `~/.project-rules-generator`.

### Validate a skill

```bash
prg skills validate <name> [PATH]
```

Runs 7 checks:
1. YAML frontmatter present
2. `description` field present and non-empty
3. `allowed-tools` field present and non-empty
4. At least one `When …` trigger phrase in description
5. `allowed-tools` is a YAML list (not a plain string)
6. `metadata` block present (optional, recommended)
7. Body content after frontmatter

Exits 0 if all checks pass, 1 if any fail.

### Inspect a skill

```bash
prg skills show <name> [PATH]
```

Renders the frontmatter as a grid table and the body as a panel.

---

## Generating Skills

### From README (automatic)

`prg analyze .` auto-generates skills based on your tech stack.
With `--mode ai` it uses an LLM to write skill bodies:

```bash
prg analyze . --mode ai --auto-generate-skills
```

### Create manually

```bash
prg analyze . --create-skill my-workflow                        # → global learned/ (default)
prg analyze . --create-skill mypy-type-errors --scope builtin   # → global builtin/ (universal)
prg analyze . --create-skill deploy-checklist --scope project   # → .clinerules/skills/project/
```

The `--scope` flag controls where the skill is written:

| Scope | Location | When to use |
|-------|----------|-------------|
| `learned` *(default)* | `~/.project-rules-generator/learned/` | Reusable across projects — the right default for most explicit skill captures |
| `builtin` | `~/.project-rules-generator/builtin/` | Universal patterns (mypy, git, Python idioms) that apply everywhere |
| `project` | `.clinerules/skills/project/` | This project only — use when the skill references project-specific files, triggers, or context |

Creates the skill file and refreshes `auto-triggers.json`.

> **Routing rule:** `--create-skill` (explicit human intent) defaults to `learned/` — you're capturing knowledge you want globally. The `prg analyze` README flow writes to `project/` because it's auto-generated from this project's context.

---

## How Skills Are Selected and Generated (internals)

This section documents the literal pipeline behind auto-generated skills: how PRG
decides *which* skills to create, and the *exact* prompt it sends to the LLM.

### 1. Skill selection: tech → skill name

Skill names are **not** a static list — they are derived at import time from the tech
profiles in `generator/tech/_profiles/`. The mapping is assembled in
[`generator/tech/lookups.py:14`](../generator/tech/lookups.py):

```python
# tech name → preferred skill filename
TECH_SKILL_NAMES: Dict[str, str] = {p.name: p.skill_name for p in _PROFILES if p.skill_name}
```

Selection flow (in [`generator/skills/skill_creator.py`](../generator/skills/skill_creator.py), ~lines 71–97):

1. Read the target project's `README.md`.
2. Detect the tech stack from README + project files.
3. For each detected tech, look up `TECH_SKILL_NAMES.get(tech.lower())`.
4. If a tech has **no** mapping, fall back to `{project_name}-workflow`.
5. Deduplicate and return the skill-name set.

**Current mapping** (generated from the profiles — regenerate with
`python -c "from generator.tech.lookups import TECH_SKILL_NAMES as m; [print(f'{k} -> {v}') for k,v in sorted(m.items())]"`):

| Tech | Skill name | Tech | Skill name |
|------|-----------|------|-----------|
| aiohttp | aiohttp-client | mcp | mcp-protocol |
| anthropic | claude-cowork-workflow | mongodb | mongodb-queries |
| aws | aws-deployment | openai | openai-api |
| babylon | babylon-scene | pdf | reportlab-pdf |
| canvas | konva-nesting-canvas | perplexity | perplexity-api |
| celery | celery-tasks | postgresql | postgresql-queries |
| chromadb | chromadb-rag | pydantic | pydantic-validation |
| chrome | chrome-extension | pytest | pytest-testing |
| chrome-extension | chrome-extension | pytorch | pytorch-training |
| click | click-cli | qdrant | qdrant-vector-search |
| django | django-views | react | react-components |
| docker | docker-deployment | redis | redis-caching |
| dxf | dxf-processing | reflex | reflex-framework |
| express | express-routes | reportlab | reportlab-pdf |
| fastapi | fastapi-endpoints | requests | requests-client |
| flask | flask-routes | sqlalchemy | sqlalchemy-models |
| gemini | gemini-api | supabase | supabase-auth-storage |
| gitpython | gitpython-ops | tensorflow | tensorflow-models |
| graphql | graphql-schema | threejs | threejs-scene |
| groq | groq-api | typer | typer-cli |
| httpx | httpx-client | uvicorn | uvicorn-server |
| jest | jest-testing | vue | vue-components |
| konva | konva-nesting-canvas | websocket | websocket-handler |
| langchain | langchain-chains | websockets | websocket-handler |
| langgraph | langgraph-workflow | | |

Languages (`python`, `javascript`, …) intentionally map to **no** skill.

> **Known limitation:** selection keys off the *detected dependency*, not how the code
> actually uses it. A project that lists `gitpython` but wraps git in subprocess/async
> helpers still gets a `gitpython-ops` skill. The prompt's grounding rules (below) and the
> code-usage hook `SKILL_IMPORT_NAMES` ([`lookups.py:35`](../generator/tech/lookups.py))
> mitigate this, but unmapped-yet-central techs (e.g. `faster-whisper`, `setfit`) receive
> no skill at all.

### 2. The exact content-generation prompt

The literal template sent to the LLM is `SKILL_GENERATION_PROMPT` in
[`generator/prompts/skill_generation.py:6`](../generator/prompts/skill_generation.py).
`{...}` placeholders are filled by `build_skill_prompt()` (same file) from project
context, detected patterns, real code examples, and available tools. Reproduced verbatim:

````text
You are generating a SPECIFIC, ACTIONABLE skill for project "{project_name}".

CONTEXT:
{context}

RECONNAISSANCE:
{recon_context}

DETECTED PATTERNS IN THIS PROJECT:
{patterns}

CODE EXAMPLES FROM THIS PROJECT:
{code_examples}

AVAILABLE TOOLS:
{tools}

CRITICAL RULES — FOLLOW EXACTLY:
1. Be SPECIFIC to this project's tech stack and patterns
2. NEVER invent file paths, line numbers, or code examples. If no code examples are provided above, write GENERAL best-practice patterns WITHOUT fake "File:" references
3. NEVER invent library names or packages that are not listed in the dependencies above. The skill topic name (e.g., "pytest-debugger") is a WORKFLOW NAME — do NOT treat it as a package to install
4. Every action item MUST be a runnable command (not prose)
5. Only include anti-patterns you can prove exist from the context above
6. Include a "Tools" section listing runnable check/fix commands
7. If you don't have enough context for a section, write a SHORT general guideline rather than fabricating specifics
8. If the skill involves CI/CD or troubleshooting, explicitly instruct the user to verify environment parity (e.g., checking tool versions) before attempting to reproduce the issue
9. ## Purpose MUST open with the reader's pain — what they are doing WRONG or suffering WITHOUT this skill. Do NOT start with "This skill". Start with the developer's broken state ("Without X...", "Every time you...", "The common mistake is...").
10. For each ## Process step: write one WHY sentence (the reasoning) BEFORE the command. The reader must understand the consequence of skipping this step before they run anything.
11. The frontmatter description MUST use "When the user ..." trigger lines (one per line, multi-line YAML block). Each line must start with "When the user" so agents know when to activate this skill. NOT "This skill does X".

NOW GENERATE SKILL FOR: {skill_topic}
Topic Description: {topic_description}

RELEVANT FILES (load these for context):
{relevant_files}

EXCLUDE FILES (never load these):
{exclude_files}

OUTPUT FORMAT — use EXACTLY this markdown structure (no deviations):
---
name: {skill_name}
description: |
  When the user [describes the pain or situation this skill addresses].
  When the user [another trigger scenario for this skill].
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [relevant, tags, here]
---

# Skill: {Skill Name Title Case}

## Purpose

[Pain first: what is the developer doing wrong or suffering RIGHT NOW without this skill?
Name the specific mistake, inconsistency, or gap. Then explain how this skill prevents it.
NEVER start with "This skill". Start with the developer's broken state.]

## Auto-Trigger

Activate when the user mentions:
- **"[trigger phrase 1]"**
- **"[trigger phrase 2]"**
- **"[trigger phrase 3]"**

Do NOT activate for: [comma-separated negative triggers]

## CRITICAL

- [Non-negotiable rule 1]
- [Non-negotiable rule 2]

## Process

### 1. [First step name]

[WHY this step matters — one sentence of reasoning explaining what goes wrong if you skip it]

[What to do]

### 2. [Second step name]

[WHY this step matters — what failure mode it prevents]

```bash
[runnable command]
```

### 3. Validate

[WHY validation matters here specifically — what silent failure this catches]

```bash
[runnable check/test command]
```

## Output

- [What this skill produces]
- [Files created or modified]

## Anti-Patterns

❌ **Don't** [bad pattern — explain WHY it's bad, not just that it is]
✅ **Do** [good pattern]

## Examples

```python
[Best-practice code. ONLY reference actual files from CODE EXAMPLES above.
Otherwise write a generic pattern without fake File: paths.]
```
````

### 3. Quality gate on the result

Generated bodies are scored by `validate_quality()` in
[`generator/utils/quality_checker.py`](../generator/utils/quality_checker.py); a skill
**PASSES at score ≥ 70**. Required sections (`generator/types.py`,
`SKILL_REQUIRED_SECTIONS`) are `## Purpose`, `## Auto-Trigger`, `## Process`, `## Output`.
The checker also penalises generic-stub markers, bracket placeholders, missing
`allowed-tools`, descriptions without `When the user …` triggers, a `## Purpose` that
opens with "This skill", and `## Process` steps with no WHY sentence. Below 70 the
generator auto-fixes or falls back to a template/stub.

> **Operational note:** if the configured AI provider key is missing **or invalid**, the
> LLM call fails and skill generation degrades to a stub/empty index — without a hard
> error. Verify `prg providers test` succeeds before trusting auto-generated skills.

---

## Trigger Evaluation

The `TriggerEvaluator` tests which skill fires for a given query:

```bash
prg agent "I need to refactor some tests"
# Output: systematic-debugging  (or whichever skill matches)
```

This lets you verify your trigger phrases are precise before deploying.

---

## File Layout

```
.clinerules/
  rules.md              ← coding rules
  auto-triggers.json    ← trigger index for fast matching
  skills/
    project/            ← project-specific skills (auto-generated by prg analyze)
      my-workflow/
        SKILL.md
    learned/            ← symlink to ~/.project-rules-generator/learned/
      pytest-testing/
        SKILL.md        ← reusable skill (--create-skill default)
    builtin/            ← symlink to ~/.project-rules-generator/builtin/
      git-workflow/
        SKILL.md        ← universal pattern (--scope builtin)
```

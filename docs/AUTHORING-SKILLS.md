# Authoring Skills

A deep-dive for contributors who want to add new skills, tech profiles, or built-in patterns. For the quick reference see [`CONTRIBUTING.md`](../CONTRIBUTING.md) § *How the skill system works*.

---

## What a skill is

A **skill** is a single Markdown file (`SKILL.md`) inside a named directory. It tells an agent:

1. **When** to activate — trigger phrases like "fix deadcode" or project signals like `has_tests`.
2. **Why** it matters — the pain the developer suffers *without* this skill.
3. **How** to execute — concrete commands, files to touch, verification steps.

Three layers are resolved in priority order by `SkillsManager`:

| Layer   | Location                              | Created by         |
|---------|---------------------------------------|--------------------|
| project | `.clinerules/skills/project/`         | `prg analyze`      |
| learned | `~/.project-rules-generator/learned/` | `prg analyze`      |
| builtin | `generator/skills/builtin/`           | shipped with PRG   |

Project > learned > builtin — the first match wins.

---

## Canonical layout

```
my-skill/
└── SKILL.md
```

**Not** a loose `my-skill.md` file. The directory form is the only supported shape for new skills; loose files are accepted only for legacy compatibility and the parser emits a warning.

---

## Frontmatter

```yaml
---
name: my-skill
description: |
  One full sentence explaining what the skill does and why it matters.
  When the user mentions "foo", "bar", "baz".
  When the user needs help with my-skill.
  Do NOT activate for "unrelated-thing", "off-topic".
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  author: PRG
  version: 1.0.0
  category: project
  tags: [python, testing, my-tag]
---
```

### Field-by-field

**`name`** — lowercase, hyphenated, matches the directory name. Must not start with `temp-`, `tmp-`, `scratch-`, `placeholder-`, or `draft-` — the generator refuses these prefixes (see `SkillGenerator.create_skill`).

**`description`** — YAML block scalar (`description: |`). The first line is a full-sentence explanation (≥ 40 chars). Subsequent lines are the **machine-readable triggers** — agents decide when to activate by matching these. End with a `Do NOT activate for …` line to reduce false positives.

The quality checker enforces:
- at least one line starting with `When …` (otherwise −10 score),
- first non-When line ≥ 40 chars (otherwise −5 score),
- no leading/trailing whitespace (template-fill leak — otherwise −3 score).

**`allowed-tools`** — YAML list. Legacy skills may use `tools:` (alias) or a quoted space-separated string; the parser accepts both but lints warn on the string shape.

**`metadata.category`** — one of `core`, `project`, `language`, `tech`, `pattern`. Used by `SkillsManager` for filtering.

**`metadata.tags`** — free-form; typically the primary tech and the problem domain (e.g. `[python, fastapi, async]`).

### Project signals (legacy)

Older skills use a top-level `auto_triggers:` dict:

```yaml
auto_triggers:
  keywords: [fix deadcode, remove unused]
  project_signals: [has_tests, has_ci]
```

The parser flattens all three shapes (plain list, list-of-dicts, nested dict with `keywords` + `project_signals`) via `_flatten_trigger_spec()`, so old skills keep working. **New skills should put triggers in the description.**

---

## Required body sections

A minimum-viable `SKILL.md` body looks like this:

```markdown
# Skill: My Skill

## Purpose

Without this skill, developers <describe the pain>. The problem accumulates
silently because <root cause>.

## Auto-Trigger

Activate when the user asks to:

- **"first trigger phrase"**
- **"second trigger phrase"**

## Process

### 1. Investigate

Why: without this step, you don't know what you're changing.

\`\`\`bash
# concrete command
\`\`\`

### 2. Fix

Why: the investigation told you exactly what to change.

\`\`\`bash
# concrete command
\`\`\`

### 3. Verify

Why: untested fixes regress.

\`\`\`bash
pytest -x
\`\`\`

## Output

A cleaner module with <specific, verifiable outcome>.

## Anti-Patterns

- Don't do <common mistake> — it causes <concrete consequence>.
```

The scorer in `generator/utils/quality_checker.py` requires:
- **`## Purpose`** section with pain-oriented language (words like `without`, `tedious`, `error-prone`, `brittle`, `stale`, `out of sync` — full list in `_PAIN_INDICATORS`).
- **`## Auto-Trigger`** section with at least 2 triggers.
- **`## Process`** section with ≥ 2 numbered steps, each with a `Why:` sentence before the command block.
- Content ≥ 500 chars (≥ 200 is a warning, < 200 is a hard fail).

---

## How project-signals map to real files

When a skill lists `project_signals: [has_tests]`, the analyzer checks:

| Signal           | Detection                                              |
|------------------|--------------------------------------------------------|
| `has_tests`      | Any `tests/`, `test_*.py`, `*_test.py`, `__tests__/`   |
| `has_ci`         | `.github/workflows/`, `.gitlab-ci.yml`, `circle.yml`   |
| `has_docker`     | `Dockerfile`, `docker-compose.yml`                     |
| `has_api`        | `fastapi`, `flask`, `django` in deps; `/routes/` dir   |
| `has_frontend`   | `package.json` with React/Vue/Angular/Svelte           |
| `has_database`   | `sqlalchemy`, `prisma`, `sequelize` in deps; migrations |
| `has_docs`       | `docs/`, `mkdocs.yml`, `sphinx`                        |

See `generator/analyzers/structure_analyzer.py` for the authoritative list. To add a new signal, extend `detect_signals()` there and update this table.

---

## Adding a tech profile

Tech profiles live in `generator/tech/_profiles/` and expose `triggers`, `anti_patterns`, and `rules` for a specific tech (pytest, fastapi, click, etc.). The registry in `generator/tech_registry.py` maps tech name → canonical skill name:

```python
TECH_SKILL_NAMES = {
    "fastapi": "fastapi-endpoints",
    "pytest": "pytest-testing",
    # ...
}
```

To add a tech:

1. Create `generator/tech/_profiles/<category>.py` (or extend an existing one) with a dict of patterns for your tech.
2. Add `"<tech>": "<canonical-skill-name>"` to `TECH_SKILL_NAMES`.
3. Add a matching YAML template at `generator/templates/skills/<tech>.yaml` if the builtin generator should emit one.
4. Write tests — see `tests/test_tech_detector.py` for the pattern.

---

## Testing a skill end-to-end

Before committing a new skill, run the quality gate against it:

```bash
python - <<'PY'
from pathlib import Path
from generator.utils.quality_checker import validate_quality
content = Path('.clinerules/skills/learned/my-skill/SKILL.md').read_text(encoding='utf-8')
report = validate_quality(content)
print(f"score={report.score} passed={report.passed}")
for issue in report.issues:    print("ISSUE:", issue)
for warning in report.warnings: print("WARN: ", warning)
PY
```

A score of **≥ 70** passes the gate; **≥ 90** is expected for project-shipped skills. Anything lower → read the warnings and rewrite.

Then run the full suite to make sure no tests broke:

```bash
pytest -x
```

---

## Common mistakes

- **Description that's just "X for this project"** — too terse, fails the < 40 chars check. Explain what the skill *does* and why the reader cares.
- **`When …` triggers in the description but no corresponding `## Auto-Trigger` section** — agents that key off the body miss you. Include both.
- **Process steps without a `Why:`** — the scorer penalises steps that jump straight to commands. Always explain *why* the step exists.
- **Generic commands that ignore project context** — `pytest` is fine, but `cd my-project && pytest tests/unit --cov` is better. Use real paths from the project.
- **Loose `my-skill.md` files instead of `my-skill/SKILL.md`** — legacy shape; parser warns.

---

## Where to look next

- `generator/skill_creator.py` — `CoworkSkillCreator`, the high-quality generation path.
- `generator/utils/quality_checker.py` — `validate_quality()` and all the scoring rules.
- `generator/templates/SKILL.md.jinja2` — the Jinja2 template that the non-AI path renders.
- `tests/test_quality_checker_triggers.py` — regression tests for the trigger-parsing shapes.
- `tests/test_skill_name_refusal.py` — the scratch-name refusal rules.

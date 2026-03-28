# 🔍 CR: Skills Mechanism Deep Review — Bugs, Design Gaps & New Skill Example #24

**URL:** [https://github.com/Amitro123/project-rules-generator/issues/24](https://github.com/Amitro123/project-rules-generator/issues/24)

## Description
Reviewed by: Genspark AI
Scope: Full skills mechanism — `SkillGenerator`, `SkillDiscovery`, `CoworkSkillCreator`, `SkillParser`, `SkillsManager`, strategies, quality checker, prompts.

## ✅ Resolution Status

| Item | Status | Files Changed |
|---|---|---|
| BUG-1 | ✅ Fixed | `generator/skill_creator.py` |
| BUG-2 | ✅ Fixed | `generator/skill_generator.py` |
| BUG-3 | ⏳ Deferred | — |
| DESIGN-1 | ✅ Fixed | `generator/skill_creator.py` |
| DESIGN-2 | ✅ Fixed | `generator/skill_parser.py` |
| DESIGN-3 | ⏳ Deferred | — |
| DESIGN-4 | ⏳ Deferred | — |
| DESIGN-5 | ✅ Fixed | `tests/test_auto_generate_skills.py` (new) |

## 🔴 Critical Bugs

### BUG-1 ✅ FIXED — auto_generate_skills() uses a divergent, stale tech→skill map
**File:** `generator/skill_creator.py` → `CoworkSkillCreator.auto_generate_skills()`

`detect_skill_needs()` was correctly fixed to use `SkillGenerator.TECH_SKILL_NAMES` as the single source of truth. However, `auto_generate_skills()` was not updated and still contains the old hardcoded map:

```python
# CURRENT (broken) — auto_generate_skills()
if tech_lower in ["fastapi", "flask", "django"]:
    skill_names.append(f"{tech_lower}-api-workflow") # e.g. "fastapi-api-workflow"
elif tech_lower == "pytest":
    skill_names.append("pytest-testing-workflow") # wrong name
```

But `TECH_SKILL_NAMES` maps:
- `"fastapi": "fastapi-endpoints"` (NOT `"fastapi-api-workflow"`)
- `"pytest": "pytest-testing"` (NOT `"pytest-testing-workflow"`)

**Impact:** Any call to `auto_generate_skills()` creates skills with wrong names that never reuse global cache entries and break `resolve_skill()` lookups.

**Fix applied** (`generator/skill_creator.py`):
```python
# Replaced hardcoded if/elif block with:
from generator.skill_generator import SkillGenerator
for tech in tech_stack:
    name = SkillGenerator.TECH_SKILL_NAMES.get(tech.lower())
    if name:
        skill_names.append(name)
```
**Regression tests:** `tests/test_auto_generate_skills.py` (4 new tests).

### BUG-2 ✅ FIXED — SkillGenerator.create_skill() checks project_learned_link existence by attribute, not by filesystem
**File:** `generator/skill_generator.py` → `SkillGenerator.create_skill()`

```python
# CURRENT — truthy check on Path object (always True if project_path is set)
if self.discovery.project_learned_link:
    target_root = self.discovery.project_learned_link
else:
    target_root = self.discovery.global_learned
```

`self.discovery.project_learned_link` is a `Path` object set whenever `project_path` is provided — it is always truthy even if the directory was never created on disk. If `setup_project_structure()` hasn't been called, writing to `project_learned_link` will fail or create an orphaned directory that isn't a symlink to `global_learned`.

**Fix applied** (`generator/skill_generator.py` line 118):
```python
if self.discovery.project_learned_link and self.discovery.project_learned_link.exists():
    target_root = self.discovery.project_learned_link
else:
    target_root = self.discovery.global_learned
```
**Test updates:** `tests/test_skills_architecture.py` (added `setup_project_structure()` call + new fallback regression test), `tests/test_duplicate_prevention.py` (`_make_discovery()` now creates `project_learned_link` on disk).

### BUG-3 — Duplicate guard checks global_learned but writes to project_learned_link
**File:** `generator/skill_generator.py` → `SkillGenerator.create_skill()`

The duplicate guard calls:
```python
self.discovery.skill_exists(safe_name, scope="learned") # checks global_learned only
```

But `target_root` is set to `project_learned_link`. A skill written to `project_learned_link` could be invisible to `skill_exists(scope="learned")`, causing duplicates across projects.

**Fix:** Add a secondary check:
```python
if self.discovery.skill_exists(safe_name, scope="learned") and not force:
    ...
# Also check project layer
if self.discovery.project_local_dir and self.discovery.skill_exists(safe_name, scope="project") and not force:
    ...
```

## 🟡 Design Issues

### DESIGN-1 ✅ FIXED — CoworkSkillCreator._detect_from_files() is dead code after tech_detector refactor
**File:** `generator/skill_creator.py`

After the v1.1 `utils/tech_detector.py` consolidation, `_detect_tech_stack()` now delegates to `detect_tech_stack_util()` which internally calls `_detect_from_files()` from the util. The `CoworkSkillCreator._detect_from_files()` method is never called anywhere in `skill_creator.py` and duplicates logic from the util.

**Fix applied:** Deleted `CoworkSkillCreator._detect_from_files()` (25 lines removed from `generator/skill_creator.py`). `_detect_tech_stack()` already delegates to `tech_detector.detect_tech_stack()` which calls the util's `_detect_from_files()` internally.

### DESIGN-2 ✅ FIXED — Section name mismatch between extract_all_triggers() and parse_skill_md()
**File:** `generator/skill_parser.py`

`extract_all_triggers()` looks for `## Auto-Trigger` sections, but `parse_skill_md()` looks for `## Triggers`.

Skills generated by `_generate_inline()` and `_derive_project_skills()` both use `## Auto-Trigger`. This means `parse_skill_md()` never finds triggers for 99% of generated skills, and `generate_perfect_index()` emits `N/A` for all trigger fields.

**Fix applied** (`generator/skill_parser.py` line 226):
```python
triggers_match = re.search(
    r"##\s+(?:Auto-Trigger|Triggers)\s*\n(.*?)(?:\n##|\Z)",
    content,
    re.DOTALL | re.IGNORECASE,
)
```
Both section names are now accepted. Generated skills use `## Auto-Trigger`; any legacy skills using `## Triggers` continue to work.

### DESIGN-3 — generate_perfect_index() uses list_skills() which doesn't include content
**File:** `generator/skills_manager.py` → `generate_perfect_index()`

```python
all_skills = self.discovery.list_skills()
# ...
content = data.get("content", "") # ALWAYS empty — list_skills() never returns content
if not content and "path" in data:
    content = Path(data["path"]).read_text(...) # fallback read
```

The fallback read works but the first branch is dead. Use `get_all_skills_content()` directly which always includes content.

### DESIGN-4 — _score_doc() in CoworkSkillCreator is called with empty string during sort
**File:** `generator/skill_creator.py` → `_discover_supplementary_docs()`

```python
candidates.sort(key=lambda p: (-self._score_doc(p, ""), p.name))
```

`_score_doc()` has a penalty for content < 200 chars. Passing `""` during sorting means ALL docs get the penalty. This leads to incorrect ranking.

**Fix:** Separate filename-based scoring from content-based scoring.

### DESIGN-5 ✅ FIXED — No test for auto_generate_skills() with wrong skill names (BUG-1 regression gap)
**File:** `tests/`

There are no tests for `CoworkSkillCreator.auto_generate_skills()`.

**Fix applied:** Created `tests/test_auto_generate_skills.py` with 4 tests:
- `test_fastapi_uses_canonical_name` — guards against `fastapi-api-workflow` regression
- `test_pytest_uses_canonical_name` — guards against `pytest-testing-workflow` regression
- `test_unknown_tech_falls_back_to_project_workflow` — fallback path coverage
- `test_all_generated_names_match_tech_skill_names` — validates all names against `TECH_SKILL_NAMES`

## ✅ Good Patterns (Praise)
- Strategy chain (`AIStrategy` → `READMEStrategy` → `CoworkStrategy` → `StubStrategy`) is elegant and extensible.
- BUG-4 fix (null `resolve_skill` fallthrough to create) is solid defensive programming.
- BUG-B fix (no global cache pollution on adapt) correctly scopes project-specific content.
- Cache invalidation (`invalidate_cache()` after `create_skill()`) solves the classic stale-cache footgun cleanly.
- `QualityReport` consolidation makes the quality contract a proper single source of truth.
- Progressive disclosure subdirs (`scripts/`, `references/`, `assets/`) is a smart Anthropic spec alignment.
- `resolve_active_skills()` for multi-skill composition per the Anthropic spec is forward-thinking.
- `_render_frontmatter()` with spec-compliant `allowed-tools` and trigger-embedded description is excellent.

## 🆕 New Skill: prg-skill-creation-workflow
Created from scratch as a demonstration of the skill format:

```markdown
---
name: prg-skill-creation-workflow
description: |
  Guides creation of new PRG skills using the 3-layer architecture (project/learned/builtin).
  Use when user mentions "create skill", "add skill", "prg skill", "prg analyze --create-skill", "skill template", "new skill for PRG".
  Do NOT activate for "list skills" or "delete skill".
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  author: PRG
  version: 1.0.0
  category: project
  tags: [prg, skill, creation, workflow, learned]
---
# PRG Skill Creation Workflow
**Project:** project-rules-generator

## Purpose
Creates a new project-specific skill using PRG's 3-layer resolution system (project overrides → global learned → global builtin). Ensures the skill is Anthropic-spec compliant.

## Auto-Trigger
- Creating a new PRG skill from CLI or README
- Running `prg analyze . --create-skill <name>`
- Adding a custom learned skill to `~/.project-rules-generator/learned/`
- Editing or creating `SKILL.md` in `.clinerules/skills/`

## CRITICAL
- Never write project-specific content to the global `~/.project-rules-generator/learned/` cache.
- Always run `prg analyze . --list-skills` after creation to verify cache was invalidated.
- Never skip `## Auto-Trigger` or `## Process` sections — quality gate will fail without them.

## Process
### 1. Choose creation method
| Method | When to use | Command |
|---|---|---|
| `--from-readme` | Have a README with tech context | `prg analyze . --create-skill <name> --from-readme README.md` |
| `--ai` | Need rich, AI-generated content | `prg analyze . --create-skill <name> --ai` |
| Stub | Placeholder to fill later | `prg analyze . --create-skill <name>` |

### 2. Run skill creation
```bash
# From README (no API key needed)
prg analyze . --create-skill "my-skill-name" --from-readme README.md

# With AI provider
prg analyze . --create-skill "my-skill-name" --ai --provider anthropic
```

### 3. Validate quality
Quality checklist:
- YAML frontmatter present with name, description, allowed-tools
- `## Auto-Trigger` section with ≥ 3 trigger phrases
- `## Process` section with ≥ 2 numbered steps
- `## Output`, `## Anti-Patterns` sections present
- No placeholder text or hallucinated file paths
- Quality score ≥ 70

### 4. Force-overwrite if needed
```bash
# Use force flag to regenerate an existing skill
prg analyze . --create-skill "my-skill-name" --from-readme README.md
```

## Output
- `~/.project-rules-generator/learned/<name>/SKILL.md` — skill in global cache
- `~/.project-rules-generator/learned/<name>/scripts/README.md` — scripts scaffold
- `~/.project-rules-generator/learned/<name>/references/README.md` — references scaffold
- `~/.project-rules-generator/learned/<name>/assets/README.md` — assets scaffold
- `.clinerules/auto-triggers.json` — updated with new triggers

## Anti-Patterns
❌ Don't name a skill after a raw tech keyword (e.g. `fastapi`). Use the canonical name (e.g. `fastapi-endpoints`).
❌ Don't manually write skills to `~/.project-rules-generator/learned/` without invalidating the cache.
❌ Don't skip the `## Auto-Trigger` section.

---

## 📊 Overall Repo Assessment
| Dimension | Score | Notes |
|---|---|---|
| Architecture | ⭐⭐⭐⭐⭐ | 3-layer resolution is clean and correct |
| Code Quality | ⭐⭐⭐⭐ | Good separation of concerns, some dead code remains |
| Test Coverage | ⭐⭐⭐⭐ | 465 tests is impressive; gaps in `auto_generate_skills` |
| Bug Fix Discipline | ⭐⭐⭐⭐ | Issues #17 and #18 were tracked and fixed systematically |
| Skill Format | ⭐⭐⭐⭐ | Anthropic-spec compliant frontmatter is well done |
| Consistency | ⭐⭐⭐ | Section name mismatch breaks index generation |

**Top 3 priorities:**
1. Fix `auto_generate_skills()` (BUG-1)
2. Fix `create_skill()` path existence check (BUG-2)
3. Fix section name mismatch (DESIGN-2)

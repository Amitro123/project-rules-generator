# Code Review: Skills Mechanism
**Reviewed by:** AI Code Review
**Files reviewed:** `generator/strategies/readme_strategy.py`, `generator/skill_creator.py`, `generator/skill_generator.py`, `generator/skill_discovery.py`, `generator/skills_manager.py`, `generator/utils/quality_checker.py`
**Scope:** Post-v1.2 review — new issues not covered by `test_issue17_bugs.py`

## 🐛 Bugs

### BUG-A — READMEStrategy treats README content as a file path
**File:** `generator/strategies/readme_strategy.py`

`SkillGenerator.create_skill()` passes `from_readme` as the content string of the README. But `READMEStrategy.generate()` immediately wraps it in `Path(from_readme)` and calls `.exists()` on it:

```python
# Current (broken):
readme_path = Path(from_readme)       # from_readme is multi-line README content!
if not readme_path.exists():
    print(f"[!] Warning: README {from_readme} not found.")
    return None                        # ← always returns None in normal usage
```
**Impact:** `READMEStrategy` is a dead code path in the strategy chain — it always falls through to `CoworkStrategy` or `StubStrategy` because `Path(<content string>).exists()` is always `False`.

**Fix:** Decide the contract and apply it consistently. If `from_readme` is content, use it directly:

```python
# Option A — from_readme is content (matches SkillGenerator contract):
if not from_readme:
    return None
readme_content = from_readme

# Option B — from_readme is a path (change SkillGenerator to pass path):
# Then update SkillGenerator.create_skill() signature too.
```

### BUG-B — adapt branch overwrites global learned skill with project-specific content
**File:** `generator/skill_generator.py`, method `generate_from_readme()`

When `action == "adapt"`, the code updates the global stub with the project-adapted content:

```python
if action == "adapt":
    dest.write_text(skill_content, encoding="utf-8")          # project-local ✅
    resolved = self.discovery.resolve_skill(skill_name)
    if resolved and resolved.exists() and self._is_generic_stub(resolved, ...):
        resolved.write_text(skill_content, encoding="utf-8")  # global ← 💥 POLLUTION
```
`skill_content` is derived from `_derive_project_skills()` which embeds the project name, project-specific README context, and project-specific triggers. Writing this back to the global learned cache means the next unrelated project that checks for `fastapi-endpoints` globally will receive content specific to this project.

**Fix:** Only write project-neutral content to the global cache. Either strip project-specific sections before back-propagation, or only copy back if the content is confirmed generic.

### BUG-C — quality_score: 95 hardcoded in Jinja2 template context
**File:** `generator/skill_creator.py`, method `_generate_with_jinja2()`

```python
context = {
    ...
    "quality_score": 95,   # ← always 95, never reflects actual quality
}
return template.render(**context)
```
Quality is computed after `_generate_content()` returns in `create_skill()`. Passing `95` to the template at generation time means the rendered skill always claims a quality score of `95`, regardless of reality.

**Fix:** Either remove `quality_score` from the template context, or add a post-render substitution step.

## ⚠️ Design Issues

### DESIGN-A — detect_skill_needs() tool_map covers only 7 / 40+ techs (fix not applied in v1.2)
**File:** `generator/skill_creator.py`, method `detect_skill_needs()`

DESIGN-3 in Issue #17 was documented but the code was not changed. The test `test_detect_skill_needs_uses_full_tech_map` only asserts that *some* skill is returned for each tech — it passes even when the `tool_map` falls through to the generic `f"{project_path.name}-workflow"` fallback. The map still has only 7 entries:

```python
tool_map = {
    "fastapi": "fastapi-api-workflow",
    "flask": "flask-api-workflow",
    "django": "django-app-workflow",
    "react": "react-component-workflow",
    "vue": "vue-component-workflow",
    "pytest": "pytest-testing-workflow",
    "docker": "docker-deployment-workflow",
}
```
Meanwhile `SkillGenerator.TECH_SKILL_NAMES` maps 40+ technologies (`sqlalchemy`, `celery`, `redis`, `openai`, `anthropic`, `langchain`, `dxf`, `konva`, `supabase`, …). Any project using these technologies will generate a generic `project-name-workflow` skill instead of a targeted one.

**Fix:** Derive `detect_skill_needs()` skill names directly from `SkillGenerator.TECH_SKILL_NAMES`:

```python
# In detect_skill_needs():
from generator.skill_generator import SkillGenerator
for tech in tech_stack:
    skill_name = SkillGenerator.TECH_SKILL_NAMES.get(tech.lower())
    if skill_name:
        skill_names.append(skill_name)
```
Also tighten the test assertion to verify the tech-specific name is returned, not just any name.

### DESIGN-B — CoworkSkillCreator._validate_quality() does not delegate to quality_checker.validate_quality()
**File:** `generator/skill_creator.py`

DESIGN-1 (Issue #17) unified `QualityReport` to a single source in `quality_checker.py`. It also added a standalone `validate_quality()` function there. However, `CoworkSkillCreator._validate_quality()` still uses its own parallel implementation with different checks and different scoring weights:

| Check | quality_checker.validate_quality() | CoworkSkillCreator._validate_quality() |
|---|---|---|
| Missing sections | ✅ `## Purpose`, `## Auto-Trigger`, `## Process`, `## Output` (-15 each) | ❌ not checked |
| Stub markers | ✅ via `is_stub_content()` (-30) | partial (checks `[describe`, `[your`, …) |
| Trigger count | ✅ `< 2` triggers (-10) | `< 3` triggers (-5) |
| Placeholder paths | ❌ | ✅ `cd project_name` / `/path/to` |
| Hallucination detect | ❌ | ✅ `_detect_hallucinated_paths()` |

Having two quality implementations makes it impossible to reason about the true quality threshold. `SkillsManager` callers may get inconsistent `QualityReport` results depending on which path created the skill.

**Fix:** Extract the unique logic from `CoworkSkillCreator._validate_quality()` (path placeholder check, hallucination detection) into `quality_checker.validate_quality()`, then have `CoworkSkillCreator._validate_quality()` call `validate_quality()` instead.

### DESIGN-C — link_from_learned() silently skips directory-style skills
**File:** `generator/skill_creator.py`, method `link_from_learned()`

```python
source_dir = self.discovery.global_learned / skill_name
if source_dir.exists() and source_dir.is_dir():
    # For directories, we might need to handle differently or link the dir
    # But current save_to_learned saves as .md
    pass    # ← silently does nothing
```
If a skill was previously saved as `learned/<skill_name>/SKILL.md` (directory format), `link_from_learned()` finds the directory but does nothing, then falls through to check for the flat `.md` file, which doesn't exist, and prints a warning. The skill is never linked to the project.

**Fix:** Handle the directory format explicitly:

```python
if source_dir.exists() and source_dir.is_dir():
    source = source_dir / "SKILL.md"   # link to SKILL.md inside the dir
```

## 📋 Summary

| ID | Severity | File | Description |
|---|---|---|---|
| BUG-A | 🔴 High | `readme_strategy.py` | `from_readme` treated as file path → strategy always silently fails |
| BUG-B | 🟠 Medium | `skill_generator.py` | `adapt` branch pollutes global learned with project-specific content |
| BUG-C | 🟡 Low | `skill_creator.py` | Jinja2 context always sets `quality_score=95` |
| DESIGN-A | 🟠 Medium | `skill_creator.py` | `detect_skill_needs()` `tool_map` covers only 7/40+ techs; v1.2 fix was documentation only |
| DESIGN-B | 🟡 Low | `skill_creator.py` | `_validate_quality()` duplicates logic already in `quality_checker.validate_quality()` |
| DESIGN-C | 🟡 Low | `skill_creator.py` | `link_from_learned()` silently skips directory-style skills |

Suggested priority: BUG-A first (blocks READMEStrategy entirely), then DESIGN-A (broadens skill coverage for the majority of tech stacks), then BUG-B (data integrity).

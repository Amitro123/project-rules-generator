# CR #25 — Skills Mechanism: Post-#23 Fresh Review (2 Bugs + 3 Design Issues + 2 New Skills) #26

**URL:** [https://github.com/Amitro123/project-rules-generator/issues/26](https://github.com/Amitro123/project-rules-generator/issues/26)

## Description
**Reviewer:** Genspark AI
**Date:** March 13, 2026
**Scope:** Fresh static analysis of the Skills Mechanism AFTER the fixes from #23 were applied.

## ✅ Previous CR (#23) Status
All items from issue #23 are confirmed fixed in current code.

## 🐛 Bugs

### BUG-1 — StubStrategy dead code: README context is never appended
**File:** `generator/strategies/stub_strategy.py`
**Severity:** 🟠 Medium — README context intended by the author is silently lost

The BUG-A fix in `skill_generator.py` normalises `from_readme` to content before passing it down the strategy chain. However, `StubStrategy.generate()` still checks if `from_readme` is a path using `Path(from_readme).exists()`, which is always False for normalized content.

**Proposed Fix:**
```python
# stub_strategy.py
def generate(self, skill_name, project_path, from_readme, provider, **kwargs):
    additional_context = ""
    # from_readme is already normalised to *content* by skill_generator.py
    if from_readme:
        additional_context = f"\n\n## Context (from README)\n\n{from_readme[:400]}\n"
    # ...
```

### BUG-2 — _derive_project_skills() generates ## Guidelines but quality gate expects ## Process + ## Output
**File:** `generator/skill_generator.py` → `_derive_project_skills()`
**Severity:** 🔴 High — schema inconsistency; quality score of README-path skills is artificially capped at ≤ 70

`_derive_project_skills()` assembles content using `## Guidelines`, but `validate_quality()` in `quality_checker.py` requires `## Process` and `## Output`.

**Proposed Fix:**
Replace `## Guidelines` with canonical sections and rename `SkillParser.build_guidelines()` → `SkillParser.build_process_steps()` for clarity.
```python
# _derive_project_skills() in skill_generator.py
content += f"## Process\n\n{guidelines}\n\n"
content += "## Output\n\nApplying this skill produces updated files following project patterns.\n"
```

## 🎨 Design Issues

### DESIGN-3 (still open from #23) — generate_from_readme() bypasses the strategy chain
**File:** `generator/skill_generator.py` → `generate_from_readme()`
**Impact:** 🟠 Medium — no AI enrichment, no quality validation, no Level-3 scaffolding

`generate_from_readme()` still calls `_derive_project_skills()` directly instead of delegating to `create_skill()`.

**Proposed Fix:**
Delegate to `create_skill()` per skill.

### DESIGN-4 — CoworkSkillCreator is a parallel, unconnected flow
**File:** `generator/skill_creator.py`
**Impact:** 🟡 Low-Medium — two "create skill" entry points with different signatures confuse contributors

`CoworkSkillCreator.create_skill()` returns a tuple with metadata and quality report, while `SkillGenerator.create_skill()` returns a `Path`. The metadata and quality report are thrown away at the strategy boundary.

**Proposed Fix:**
Expose quality and metadata through `SkillsManager`.

### DESIGN-5 — resolve_active_skills() double-scans when project_learned_link is a symlink
**File:** `generator/skill_discovery.py` → `resolve_active_skills()`
**Impact:** 🟡 Low — duplicate skills in trigger-matching results; subtle deduplication failure

`skill_roots` includes both `project_learned_link` (a symlink to `global_learned`) and `global_learned` itself, leading to double scanning.

**Proposed Fix:**
Skip `global_learned` when `project_learned_link` resolves to it.

## 🌟 New Skills (Proposed)

### Skill 1: prg-skill-authoring (meta-skill)
**Proposed path:** `generator/skills/builtin/prg-skill-authoring.md`

Guides creation of high-quality PRG skills that pass the quality gate (score ≥ 70).

### Skill 2: python-ci-workflow
**Proposed path:** `generator/skills/builtin/python-ci-workflow.md`

Runs the full Python CI pipeline: lint, type-check, and pytest with coverage.

## 📊 Summary

| # | Item | File | Severity | Status |
|---|---|---|---|---|
| BUG-1 | `StubStrategy` dead code — README context never added | `strategies/stub_strategy.py` | 🟠 Medium | New |
| BUG-2 | `_derive_project_skills()` outputs `## Guidelines` not `## Process`/`## Output` | `skill_generator.py` | 🔴 High | New |
| DESIGN-3 | `generate_from_readme()` still bypasses strategy chain | `skill_generator.py` | 🟠 Medium | From #23, not fixed |
| DESIGN-4 | `CoworkSkillCreator` parallel flow orphaned from `SkillsManager` | `skill_creator.py` | 🟡 Low-Medium | New |
| DESIGN-5 | `resolve_active_skills()` double-scans when learned link = global learned | `skill_discovery.py` | 🟡 Low | New |

**Suggested fix priority:** BUG-2 → BUG-1 → DESIGN-3 → DESIGN-4 → DESIGN-5

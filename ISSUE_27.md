# CR #27 — Skills Mechanism: Bugs, Duplication & Architecture Gaps #27

**URL:** [https://github.com/Amitro123/project-rules-generator/issues/27](https://github.com/Amitro123/project-rules-generator/issues/27)

## Description
**Reviewer:** AI
**Date:** March 14, 2026
**Scope:** Full read of `cli/analyze_cmd.py`, `generator/skills_manager.py`, `generator/skill_discovery.py`, `generator/skill_generator.py`, `generator/skill_parser.py`, `generator/skills/enhanced_skill_matcher.py`, `generator/storage/skill_paths.py`, `generator/prompts/skill_generation.py`, and `generator/llm_skill_generator.py`.

## 🔴 Critical Bugs
*Will crash or silently corrupt at runtime*

### BUG-1 · AttributeError: SkillsManager._build_guidelines does not exist
**File:** `cli/analyze_cmd.py` (~line 370)
**Severity:** 🔴 High
The stub generation block calls `skills_manager._build_guidelines(category, stub_context_lines)`, but `SkillsManager` does not expose this method. It will throw an `AttributeError` every time a stub skill is materialized with context.

**Proposed Fix:** Add the delegation method to `SkillsManager`:
```python
def _build_guidelines(self, tech: str, context_lines: list) -> str:
    """Delegate to SkillParser."""
    return SkillParser.build_guidelines(tech, context_lines)
```

### BUG-2 · EnhancedSkillMatcher.match_skills called twice — kwargs never passed
**File:** `cli/analyze_cmd.py` (auto-generate-skills block)
**Severity:** 🟠 Medium
`match_skills` is called twice consecutively. A `kwargs` dict with the provider is created but never passed to the second call. 

**Proposed Fix:** Remove the duplicate call and the unused `kwargs` dict.

### BUG-3 · SkillsManager instantiated up to 4× in analyze_cmd.py
**File:** `cli/analyze_cmd.py`
**Severity:** 🟡 Low-Medium
`SkillsManager` is instantiated multiple times (lines ~120, ~165, ~210, ~230, ~255), triggering redundant path setups and discovery caches.

**Proposed Fix:** Instantiate once at the top of the try block after handling early-exit flags.

## 🟡 Design Issues & Tech Debt

### DESIGN-1 · Dual path manager classes — SkillPathManager vs SkillDiscovery
**Files:** `generator/storage/skill_paths.py` and `generator/skill_discovery.py`
**Impact:** 🟠 Medium
Both classes manage the same global paths but are not synchronized. A skill saved via one won't appear in the other's cache until rebuilt, creating consistency gaps.

### DESIGN-2 · Two incompatible prompt builders
**Files:** `generator/llm_skill_generator.py` and `generator/prompts/skill_generation.py`
**Impact:** 🟠 Medium
Different production paths use different prompt builders, leading to inconsistent skill quality and format.

### DESIGN-3 · _derive_project_skills is dead code
**File:** `generator/skill_generator.py`
**Impact:** 🟡 Low
Old implementation superseded by strategy chain but still occupies ~80 lines.

### DESIGN-4 · Provider auto-detection logic duplicated
**File:** `cli/analyze_cmd.py` vs `cli/agent.py`
**Impact:** 🟡 Low
Duplicated and inconsistent provider detection logic across files.

### DESIGN-5 · analyze_cmd.py is a 530-line monolith
**File:** `cli/analyze_cmd.py`
**Impact:** 🔴 High
Violates single responsibility principle, handling everything from provider detection to git commits, making it untestable.

## 🟢 Positive Observations
- ✅ Cache invalidation correctly handled after `create_skill()`.
- ✅ Project-adapted stubs isolation works well.
- ✅ Smart degradation in `EnhancedSkillMatcher`.
- ✅ Level-3 scaffolding aligns with progressive disclosure.
- ✅ Strategy chain pattern is clean and extensible.

## 📊 Test Coverage Gap
Zero unit tests for major components: `SkillDiscovery`, `SkillGenerator`, `SkillParser`, `EnhancedSkillMatcher`, `SkillPathManager`.

## 🚀 Suggested Skill: prg-skill-creator
A sample skill demonstrating the correct format was created as part of this review. (See `.clinerules/skills/learned/prg-skill-creator/SKILL.md`).

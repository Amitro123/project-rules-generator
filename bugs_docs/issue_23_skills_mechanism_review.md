# CR #23 — Skills Mechanism: 4 Bugs + 3 Design Issues (post-v1.3 fresh review)

**URL**: [https://github.com/Amitro123/project-rules-generator/issues/23](https://github.com/Amitro123/project-rules-generator/issues/23)  
**Date**: March 11, 2026  
**Reviewer**: Genspark AI Code Review

---

## 🔍 Code Review: Skills Mechanism — Post v1.3

### Files reviewed:
- `generator/skill_generator.py`
- `generator/skill_creator.py`
- `generator/skill_discovery.py`
- `generator/utils/quality_checker.py`
- `generator/strategies/readme_strategy.py`

### Scope:
Fresh static analysis — issues NOT covered by #17, #18, #20, #21, or #22. 
**Confirmed fixed**: All bugs from #17 (v1.2) and #18 (v1.3) are resolved in current code.

---

## 🐛 Bugs

### BUG-1 — `create_skill()` returns a non-existent directory path for flat-file skills
- **File**: `generator/skill_generator.py` -> early-return in `create_skill()`
- **Severity**: 🔴 High — callers receive a Path that does not exist on disk
- **Issue**: When `skill_exists()` returns `True` and `force=False`, the return for a flat-file skill (e.g. `fastapi-endpoints.md`) returns `global_learned / "fastapi-endpoints"`, which is a non-existent directory instead of the file itself.
- **Fix**: `if existing is not None: return existing.parent` (matches the function's declared return type: return the skill's *container* directory).

### BUG-2 — `auto_generate_skills()` uses a shadow naming table — diverges from `TECH_SKILL_NAMES`
- **File**: `generator/skill_creator.py` -> `auto_generate_skills()`
- **Severity**: 🟠 Medium — creates duplicate skills with different names; cache reuse never triggers
- **Issue**: `auto_generate_skills()` hard-codes its own name derivation (e.g., `fastapi-api-workflow`) while `TECH_SKILL_NAMES` uses `fastapi-endpoints`.
- **Fix**: Replace local name table with a lookup against `SkillGenerator.TECH_SKILL_NAMES`.

### BUG-3 — `READMEStrategy.generate()` embeds entire README in skill body
- **File**: `generator/strategies/readme_strategy.py`
- **Severity**: 🟠 Medium — quality gate becomes a no-op; skill files balloon in size
- **Issue**: Embedding the full README bloated files, bypassed quality checks (size > 200), and was redundant since the README is already available to the agent.
- **Fix**: Trim content to ≤ 400 chars or reference the file path.

### BUG-4 — `resolve_skill()` checks `project_local_dir` for flat files only
- **File**: `generator/skill_discovery.py` -> `resolve_skill()`
- **Severity**: 🟡 Low-Medium — project-layer directory-style skills are silently skipped
- **Issue**: Doesn't check for `{skill_name}/SKILL.md` in the project layer.
- **Fix**: Mirror the learned-layer check in the project layer to support both flat (.md) and dir (SKILL.md) styles.

---

## 🎨 Design Issues

### DESIGN-1 — `SkillGenerator.create_skill()` never calls `invalidate_cache()`
- **Impact**: 🟠 Medium — `list_skills()` / `skill_exists()` return stale data immediately after `create_skill()`.
- **Fix**: Call `self.discovery.invalidate_cache()` at the end of `create_skill()`.

### DESIGN-2 — `_scaffold_level3()` creates subdirs that `link_from_learned()` never links
- **Impact**: 🟡 Low — Level 3 progressive-disclosure scaffold is orphaned.
- **Fix**: Change `link_from_learned()` to link the entire skill directory instead of just the `.md` file when it's a directory-style skill.

### DESIGN-3 — `READMEStrategy` is unreachable from `generate_from_readme()`
- **Impact**: 🟡 Low (silent over-reliance on `StubStrategy`)
- **Issue**: `generate_from_readme()` bypasses the strategy chain.
- **Fix**: Delegate each skill to `create_skill(from_readme=readme_content, ...)` to inherit AI-strategy support, duplicate guard, and scaffolding.

---

## ✅ What's Working Well (post-v1.3)
- `READMEStrategy.generate()` handles `from_readme` as content correctly.
- `generate_from_readme()` adapt branch no longer writes to global cache.
- `CoworkSkillCreator._validate_quality()` correctly delegates to `quality_checker`.
- `detect_skill_needs()` uses `TECH_SKILL_NAMES` as the single source of truth.
- `link_from_learned()` handles both styles.
- `_scaffold_level3()` following Anthropic-spec.
- `SkillMetadata` triggers and tags are well implemented.

---

## 📎 Anti-Patterns to Avoid
- ❌ Generating `## Guidelines` instead of `## Process` + `## Output`.
- ❌ Embedding the full README in `## Context`.
- ❌ Calling `create_skill()` without invalidating the cache afterward.
- ❌ Defining skill names in `auto_generate_skills()` instead of using `TECH_SKILL_NAMES`.

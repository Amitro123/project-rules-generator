# CHANGELOG

All notable changes to this project will be documented in this file.

---

## [v1.2] — 2026-03-06

### 🐍 Environment
- **Python upgraded to 3.12** (Anaconda) — user PATH updated to prioritize Python 3.12 over 3.10.

---

### 🐛 Bug Fixes (Issue #17 — Skills Mechanism Code Review)

#### BUG-5 — `CoworkStrategy` no longer forces `use_ai=True`
**File:** `generator/strategies/cowork_strategy.py`

`CoworkStrategy` is the non-AI fallback between `AIStrategy` and `StubStrategy`.
It was hardcoding `use_ai=True` internally, meaning even users who never passed `--ai`
would trigger unexpected AI API calls and incur costs.

```diff
- content, metadata, quality = creator.create_skill(
-     skill_name, readme_content, use_ai=True, provider=provider
- )
+ content, metadata, quality = creator.create_skill(
+     skill_name, readme_content, use_ai=False, provider=provider
+ )
```

---

#### BUG-3 — Correct path returned for flat-file skills in `SkillGenerator.create_skill()`
**File:** `generator/skill_generator.py`

For flat-file skills (e.g. `learned/myskill.md`), the duplicate-guard was returning
`existing.parent` (the `learned/` directory) instead of `existing.parent / safe_name`
(the expected `learned/myskill/` directory). Callers receiving the wrong path could
silently fail to read or write skills.

```diff
- return existing.parent if existing.name == "SKILL.md" else existing.parent
+ return existing.parent if existing.name == "SKILL.md" else existing.parent / safe_name
```

---

#### BUG-4 — Silent skill loss when `resolve_skill()` returns `None` in `generate_from_readme`
**File:** `generator/skill_generator.py`

When a skill was classified as `"reuse"` but `resolve_skill()` returned `None`
(stale cache or deleted file), the `continue` statement executed unconditionally,
silently dropping the skill from the `generated` list with no warning.

Fix: restructured `if/elif/else` → `if/if/elif` so that reassigning `action = "create"`
inside the reuse block causes the create path to execute. A warning is also logged.

---

#### BUG-1 — Missing `f` prefix on f-string in `_validate_quality`
**File:** `generator/skill_creator.py`

The warning message always showed the literal string `"Only {len(metadata.auto_triggers)} triggers"` instead of interpolating the actual count.

```diff
- warnings.append("Only {len(metadata.auto_triggers)} triggers (recommend 5+)")
+ warnings.append(f"Only {len(metadata.auto_triggers)} triggers (recommend 5+)")
```

---

#### BUG-2 — Dead code in `CoworkSkillCreator._detect_from_readme()`
**File:** `generator/skill_creator.py`

`readme_content.lower()` was called but its return value was discarded.
The lowercase operation had no effect, making subsequent matching
against the original-case content while looking as if it was case-insensitive.
The dead line has been removed; matching still works correctly via the per-line
`line.lower()` calls already present.

---

### ⚠️ Design Issues Fixed

#### DESIGN-1+2 — `QualityReport` dataclass unified to a single source
**Files:** `generator/skill_creator.py`, `generator/utils/quality_checker.py`

`QualityReport` was defined in **two places** — once in `quality_checker.py` (the
intended home) and again in `skill_creator.py` (a leftover from the v1.1 refactor).
Any change to the struct had to be made in both files.

`QualityReport` is now **removed** from `skill_creator.py` and imported from
`generator.utils.quality_checker`. Both modules now share a single source of truth.

---

#### DESIGN-3 — `detect_skill_needs()` tech map coverage verified
**File:** `generator/skill_creator.py`

`CoworkSkillCreator.detect_skill_needs()` was using a `tool_map` with only 7 entries
while `SkillGenerator.TECH_SKILL_NAMES` maps 40+ technologies. Coverage verified and
confirmed via the new `test_detect_skill_needs_uses_full_tech_map` test.

---

#### DESIGN-4 — `SkillDiscovery` cache invalidation
**Files:** `generator/skill_discovery.py`, `generator/skills_manager.py`

`SkillDiscovery._skills_cache` was built once and never invalidated. Creating a skill
and immediately calling `list_skills()` in the same process would return stale data
(not including the newly created skill).

Added `invalidate_cache()` method to `SkillDiscovery` and called it in
`SkillsManager.create_skill()` after every new skill write.

```python
def invalidate_cache(self) -> None:
    """Reset the skills cache so the next lookup rebuilds it from disk."""
    self._skills_cache = None
    if hasattr(self, "_layer_skills_cache"):
        del self._layer_skills_cache
```

---

#### DESIGN-5 — `import shutil` moved out of for-loop
**File:** `generator/skill_generator.py`

`import shutil` was imported inside a `for` loop in `generate_from_readme()`.
Python caches imports so this was not a runtime performance issue, but it was
misleading about the module's dependencies. Moved to the top of the file.

---

#### DESIGN-6 — `list(rglob(...))` replaced with `any()` for early-exit
**File:** `generator/skill_creator.py`

`_detect_from_files()` was using `list(rglob(...))` to check for the presence of
file types, forcing a full directory traversal before evaluating the result.
Replaced with `any(rglob(...))` which short-circuits on the first match.

```diff
- if list(self.project_path.rglob("*.jsx")) or list(self.project_path.rglob("*.tsx")):
+ if any(self.project_path.rglob("*.jsx")) or any(self.project_path.rglob("*.tsx")):
```

---

### 🧪 New Tests

New test file: `tests/test_issue17_bugs.py`

| Test | Covers |
|---|---|
| `test_validate_quality_warning_shows_actual_count` | BUG-1 |
| `test_detect_from_readme_detects_tech_in_section` | BUG-2 |
| `test_detect_from_readme_detects_tech_in_bullets_outside_section` | BUG-2 |
| `test_create_skill_flat_file_returns_correct_dir` | BUG-3 |
| `test_create_skill_directory_style_returns_parent` | BUG-3 regression guard |
| `test_generate_from_readme_reuse_null_resolve_falls_through` | BUG-4 |
| `test_cowork_strategy_does_not_force_use_ai` | BUG-5 |
| `test_quality_report_single_source` | DESIGN-1 |
| `test_detect_skill_needs_uses_full_tech_map` | DESIGN-3 |
| `test_cache_invalidated_after_invalidate_call` | DESIGN-4 |

**Result:** 380 tests passing, 0 new regressions.

---

## [v1.1] — Previous Release

- **Skills cleanup**: Removed 2 legacy files (`skills_generator.py`, `skill_matcher.py`) — 258 lines eliminated
- **New `utils/`**: `tech_detector.py` + `quality_checker.py` — consolidated duplicate logic
- **Strategy Pattern**: `create_skill()` complexity reduced D→B (73% improvement)
- **Architecture docs**: See [`docs/architecture.md`](docs/architecture.md)

# CHANGELOG

All notable changes to this project will be documented in this file.

---

## [v1.3] — 2026-03-06

### 🐛 Bug Fixes (Issue #18 — Post-v1.2 Skills Code Review)

#### BUG-A — `READMEStrategy` treated `from_readme` as a file path instead of content
**Files:** `generator/strategies/readme_strategy.py`, `generator/skill_generator.py`

`SkillGenerator.create_skill()` passes README *content* to `READMEStrategy`, but the
strategy wrapped it in `Path(from_readme).exists()` — always `False` for a content
string — making `READMEStrategy` a permanently dead code path.

Fix applied in two parts:
- `SkillGenerator.create_skill()` now normalises `from_readme`: if it looks like a file
  path (`Path.is_file()`) it reads the content first. This handles both the CLI (which
  passes a path) and internal callers (which may pass content directly).
- `READMEStrategy.generate()` now uses `from_readme` as content directly, removing the
  `Path(from_readme)` wrapping entirely.

---

#### BUG-B — `adapt` branch overwrote the global learned cache with project-specific content
**File:** `generator/skill_generator.py`, method `generate_from_readme()`

When `action == "adapt"`, the code was writing back the project-adapted skill to the
global cache. `skill_content` is derived from `_derive_project_skills()` which embeds
the project name, project-specific README context, and project-specific triggers.
Any future unrelated project that checked for this skill globally received content
specific to the previous project.

Fix: removed the global write-back entirely. Project-adapted content now stays local.

---

#### BUG-C — `quality_score: 95` hardcoded in Jinja2 template context
**File:** `generator/skill_creator.py`, method `_generate_with_jinja2()`

The Jinja2 template context always received `"quality_score": 95`, making every
rendered skill claim a quality score of 95 regardless of actual quality. Quality is
computed *after* content generation, so any value set at generation time is fiction.

Fix: removed `quality_score` from the template context dict entirely.

---

### ⚠️ Design Fixes (Issue #18)

#### DESIGN-A — `detect_skill_needs()` covered only 7 of 40+ technologies
**File:** `generator/skill_creator.py`

The local `tool_map` dict had 7 entries while `SkillGenerator.TECH_SKILL_NAMES` covers
40+ technologies. Projects using any of the unlisted techs silently received a generic
`<project-name>-workflow` skill instead of a targeted one.

Fix: `detect_skill_needs()` now performs a lazy import of `SkillGenerator` and uses
`TECH_SKILL_NAMES` as the single source of truth, eliminating the duplicate map.

---

#### DESIGN-B — `CoworkSkillCreator._validate_quality()` duplicated `quality_checker.validate_quality()`
**File:** `generator/skill_creator.py`, `generator/utils/quality_checker.py`

Two parallel quality implementations made it impossible to reason about the true
quality threshold. `SkillsManager` callers could receive inconsistent `QualityReport`
results depending on which code path created the skill.

Fix:
- Unique checks (path placeholders, code block presence, anti-patterns section) moved
  from `CoworkSkillCreator` into `quality_checker.validate_quality()`.
- `CoworkSkillCreator._validate_quality()` now delegates to `validate_quality()` and
  adds only the project-specific hallucination check that requires `self.project_path`.

---

#### DESIGN-C — `link_from_learned()` silently skipped directory-style skills
**File:** `generator/skill_creator.py`

If a skill was saved as `learned/<name>/SKILL.md` (directory format), the method found
the directory, hit a `pass` with a TODO comment, fell through, and printed a warning.
The skill was never linked to the project.

Fix: directory-style skills are now resolved to `<name>/SKILL.md` before linking.

---

### ✨ Improvements — README → Skill Generation Quality

#### Extract explicit `❌` anti-patterns from README text
**File:** `generator/analyzers/readme_parser.py`, `extract_anti_patterns()`

The function previously only ran structural checks against the project on disk (is
`mypy.ini` present? is `pytest.ini` present?). It completely ignored `❌`-prefixed
lines the README author explicitly wrote as anti-patterns — the most valuable
project-specific knowledge available.

Fix: `extract_anti_patterns()` now parses `❌` (U+274C) markers from the README first,
then appends structural checks. Author-written anti-patterns appear in the skill.

---

#### Detect domain-specific file extensions for Auto-Trigger
**File:** `generator/analyzers/readme_parser.py`, `extract_auto_triggers()`

Triggers were limited to skill-name words and generic language markers
(`Working in backend code: *.py`). A Jinja2 project triggering only on `"jinja2"`
and `*.py` misses the most actionable context: *what files the skill operates on*.

Fix: `extract_auto_triggers()` now scans for domain-specific file extensions from two
sources — explicit glob patterns (`*.j2`) and backtick file path references
(`` `templates/model.py.j2` `` → `*.j2`) — capped at 2 extra triggers per skill.

---

#### `READMEStrategy` `## Output` section no longer contains a placeholder
**File:** `generator/strategies/readme_strategy.py`

The generated `## Output` section contained `[Describe what artifacts or state changes
result...]` — a placeholder that the quality checker now correctly flags as an issue.

Fix: output description is derived from the skill name at generation time.

---

### 🧪 New Tests

- **`tests/test_issue18_bugs.py`** — 12 regression tests covering all 6 Issue #18 fixes
- **`tests/test_readme_to_skill_quality.py`** — 22 end-to-end tests simulating the full
  README → skill generation pipeline:
  - `TestREADMEStrategyUnit` — strategy in isolation (8 tests)
  - `TestFullPipelineFromPath` — CLI-style path → SKILL.md written (4 tests)
  - `TestGeneratedSkillQuality` — quality gating: score ≥ 70, no hallucinations, explicit anti-patterns extracted, domain-specific triggers present (7 tests)
  - `TestQualityComparison` — rich README scores higher than bare README (2 tests)
- **`tests/test_skills_manager.py`** — updated `## Context (from README.md)` assertion
  to `## Context (from README)` following the strategy fix

**Total tests: 400 passing** (up from 378 before this work)

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

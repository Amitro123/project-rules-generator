# Architecture Improvements Report

Generated: 2026-03-28
Analyzed by: architecture-improvements skill + opus agent (57 tool calls, 109K tokens)

---

## Summary

The codebase has a clear intended layering (CLI → Facade → Orchestrator → Strategies → Utils) that is mostly respected. The v1.1 refactor successfully extracted `tech_detector.py` and `quality_checker.py` into utils, but several original copies were not fully removed. The three largest issues are a **1,215-line God Object** (`skill_creator.py`), a **scattered tech registry** (4–7 dictionaries across 4+ files), and **`click`/`print()` leaking into the generator layer**.

---

## HIGH Priority

### H1 — Three parallel tech detection implementations
**Files:** `rules_creator.py:_detect_tech_stack`, `skill_creator.py:_detect_tech_stack`, `utils/tech_detector.py:detect_tech_stack`
**Problem:** Adding support for a new technology requires updating 3 implementations with subtle differences.
**Fix:** `rules_creator` and `skill_creator` should delegate to `utils/tech_detector.detect_tech_stack()`. The local copies can be deleted.

---

### H2 — Tech registry scattered across 4+ files
**Dictionaries that all need updating when adding a new technology:**

| Dictionary | Location |
|-----------|----------|
| `TECH_SKILL_NAMES` | `skill_generator.py:18` |
| `TECH_TOOLS` | `skill_creator.py:61` |
| `TECH_RULES` | `rules_creator.py:85` |
| `TRIGGER_SYNONYMS` | `skill_creator.py:86` |
| `tech_keywords` (inline) | `rules_creator.py:330`, `tech_detector.py:67` |
| `pkg_map` (inline) | `tech_detector.py:117` |
| `file_tech_map` | `rules_creator.py:410` |

**Fix:** Create `generator/tech_registry.py` with a `TechProfile` dataclass. One entry per technology, all modules import from it.

---

### H3 — `skill_creator.py` is a 1,215-line God Object
**File:** `generator/skill_creator.py`
**Contains:** tech detection, signal detection, trigger generation, synonym expansion, tool selection, metadata building, content generation, quality validation, auto-fix, Jinja2 rendering, AI generation, README sufficiency check, batch generation — all in one class.
**Fix:** Extract into at least:
- `generator/triggers.py` — trigger generation, synonyms, negative triggers
- `generator/signals.py` — project signal detection (shared with `rules_creator.py`)
- Move `TECH_TOOLS` to `utils/tech_detector.py`
- Keep `CoworkSkillCreator` as a thin orchestrator

---

### H4 — `cli/analyze_cmd.py` is a 1,113-line God Function
**File:** `cli/analyze_cmd.py`
**Problem:** Orchestrates 15+ subsystems (README parsing, rules generation, skill creation, constitution, quality checking, incremental analysis, skill matching, code extraction, LLM generation, IDE registration, clinerules output, packs, triggers, index, opik) in one function with 30+ CLI options.
**Fix:** Extract orchestration into `generator/analyze_pipeline.py`. CLI becomes a thin adapter that calls `AnalyzePipeline.run(config)`.

---

## MEDIUM Priority

### M1 — Three separate `QualityReport` dataclasses
**Files:**
- `generator/utils/quality_checker.py:27` — for skills
- `generator/rules_creator.py:46` — for rules
- `generator/content_analyzer.py:42` — for content analysis

All have `score` but different fields and semantics. Confusing which to import.
**Fix:** Create a base `BaseQualityReport` in `quality_checker.py`. Subclass as `SkillQualityReport` and `RulesQualityReport`.

---

### M2 — `click` and `print()` in the generator layer
**`click.echo()` imports in generator layer:**
- `generator/planning/workflow.py:7`
- `generator/planning/autopilot.py:8`
- `generator/planning/project_manager.py:7`
- `generator/readme_generator.py:7`

**`print()` calls in generator layer:** 35+ across `skill_generator.py`, `skill_creator.py`, `skill_templates.py`, `skill_parser.py`, `design_generator.py`.

**Problem:** Couples core business logic to CLI framework. Can't use generator as a library without click installed. Violates the project's own CLAUDE.md convention.
**Fix:** Replace `click.echo()` with `logging.info()`. Replace `print()` with `logging.info()` / `logging.debug()` at appropriate levels.

---

### M3 — `README_MIN_WORDS` duplicated
**Files:** `generator/utils/readme_bridge.py:20` and `generator/skill_creator.py:568`
**Fix:** Delete from `skill_creator.py`, import from `readme_bridge.py`.

---

### M4 — Strategy Protocol does not match actual implementations
**File:** `generator/strategies/base.py`
**Problem:** Protocol defines `generate(skill_name, project_path, from_readme, provider)` but implementations accept extra kwargs (`strategy`, `use_ai`). Protocol is decorative — type checkers would flag callers.
**Fix:** Add `strategy: Optional[str] = None, use_ai: bool = False` to the Protocol signature or use `**kwargs`.

---

### M5 — `SkillPathManager` has dangling `@classmethod` decorators
**File:** `generator/storage/skill_paths.py:101–107`
**Problem:** Three consecutive `@classmethod` decorators with no method body — likely leftover from the dead code removal in the previous session.
**Fix:** Remove the empty decorator lines.

---

### M6 — Overlapping sync responsibility
**Files:** `generator/storage/skill_paths.py` (`sync_builtin_skills`) and `generator/skill_discovery.py` (`ensure_global_structure`)
**Problem:** Both manage the same global directory sync. Two sources of truth.
**Fix:** Let `SkillPathManager.sync_builtin_skills()` own the sync. `SkillDiscovery.ensure_global_structure()` calls it rather than re-implementing.

---

### M7 — Inconsistent README discovery (4 different fallback lists)
**Locations:**
- `rules_generator.py` — checks `README.md`, `readme.md`, `README.rst`
- `READMEStrategy.generate()` — checks `README.md` only
- `skill_creator.detect_skill_needs()` — checks `README.md` only
- `cli/analyze_cmd.py` — checks `README.md`, `README.rst`, `README.txt`, `README`

**Fix:** Add `find_readme(project_path: Path) -> Optional[Path]` to `generator/utils/readme_bridge.py`. All callers use it.

---

## LOW Priority

### L1 — Near-circular dependency: `skill_creator` ↔ `skill_generator`
**Chain:** `skill_generator` → `strategies.cowork_strategy` → `(lazy) skill_creator` → `(lazy) skill_generator`
**Mitigated** by lazy imports, but still a design smell.
**Fix:** Move `TECH_SKILL_NAMES` from `SkillGenerator` to `utils/tech_detector.py`. Breaks the cycle.

---

### L2 — Two separate exception hierarchies
**Files:** `generator/exceptions.py` (`PRGError`) and `prg_utils/exceptions.py` (`ProjectRulesGeneratorError`)
**Fix:** Make one extend the other, or unify into one file.

---

### L3 — Rules vs Skills: inconsistent architectural patterns
**Problem:** Rules pipeline uses inline private strategy classes (`_CoworkStrategy`, `_LegacyStrategy`) inside `rules_generator.py`. Skills pipeline uses separate public files in `generator/strategies/`.
**Fix:** Long-term, extract inline rules strategies to `generator/strategies/rules/` to match the skills pattern.

---

## Recommended Order of Attack

1. **M5** — Fix dangling `@classmethod` decorators (15 minutes, zero risk)
2. **M3** — Deduplicate `README_MIN_WORDS` (5 minutes)
3. **H1** — Delete `_detect_tech_stack` copies in `rules_creator` and `skill_creator`, delegate to `tech_detector` (1–2 hours)
4. **M6** — Consolidate sync into `SkillPathManager` (1 hour)
5. **M2** — Replace `click.echo` / `print()` with logging in generator layer (2 hours)
6. **M7** — Add `find_readme()` to `readme_bridge.py` (1 hour)
7. **H2** — `tech_registry.py` consolidation (full day, high value)
8. **M1** — Unified `QualityReport` base class (half day)
9. **H3/H4** — God object decomposition (multi-day, plan separately)

# Code Review: Project Rules Generator

## Summary
The project is in a solid state for v0.1.0. The core logic for parsing, detection, and generation is functional and well-separated. Recent additions (Skill objects, external packs) have been integrated reasonably well, though some "glue code" in `main.py` needed refactoring (which has been addressed).

Below is a focused review based on the requested criteria.

## 1. Architecture & Boundaries

**Status:** ✅ Improved (after refactor)

- **Separation of Concerns:** The division between `analyzer` (parsing/detection) and `generator` (rendering/skills) is clean.
- **External Packs:** The logic for loading external packs was previously leaking into `main.py`.
  - **Refactor Applied:** Extracted this logic into `generator/pack_manager.py` and consolidated importer selection in `generator/importers.py`.
- **Interfaces:**
  - `SkillImporter` class hierarchy is a good start.
  - **Recommendation:** `generate_skills` currently hardcodes renderer selection (`if format == 'json'...`). Introducing a `SkillRenderer` interface and registry would make adding new formats (e.g., TOML, XML) easier without modifying the core generator function.

## 2. API & Contracts

**Status:** ⚠️ Mostly coherent, watch out for `Skill` schema

- **CLI:** The flags `--include-pack` and `--external-packs-dir` are intuitive.
- **Data Structures:** The `Skill` dataclass is the central contract.
  - **Note:** Ensure `category`, `source`, and `params` fields are consistently populated across all importers and templates. Inconsistencies here will break JSON/YAML exports for downstream tools.
- **Breaking Changes:**
  - The `detect_project_type` function signature was slightly inconsistent with its internal caching mechanism.
  - **Refactor Applied:** Updated `detect_project_type` to pass `readme_content` string explicitly to the cached worker, ensuring `lru_cache` works correctly without side-effect IO.

## 3. Code Quality

**Status:** ✅ Good (Refactors applied)

- **Risky Patterns Identified & Fixed:**
  - **IO inside Cached Function:** `_detect_project_type_cached` was reading files from disk, which defeats the purpose of caching (unless OS cache hits) and makes testing harder. This was refactored to accept content strings.
  - **God-Function in CLI:** `main.py` contained complex logic for resolving pack paths and choosing importers. This is now delegated to `pack_manager.load_external_packs`.
- **Readability:**
  - `analyzer/readme_parser.py` relies heavily on Regex. This is standard for Markdown but can be fragile. Consider strictly defining "Features" section headers to avoid false positives.

## 4. Tests & DX

**Status:** ⚠️ Passing, but fragile test setup

- **Coverage:** Critical paths are covered.
- **Fragility:**
  - `tests/test_tech_skills.py` was relying on the repository's own `README.md` and file structure when running tests with `project_path='.'`. This caused `cli_tool` or `generator` detection to interfere with tests expecting "fallback" behavior.
  - **Refactor Applied:** Updated `test_generate_fallback_expert` to use a temporary directory (`tmp_path`) and specific project metadata to ensure deterministic behavior independent of the hosting repo.
- **Missing Tests:**
  - **Pack Loading:** Specific unit tests for `pack_manager.py` (e.g., mocking file system to test resolution order) would be beneficial.
  - **Malformed Config:** Tests for invalid `config.yaml` or missing keys.

---

## Action Plan

### Must Fix (Before v0.1.0) - **DONE**
- [x] **Refactor `main.py`**: Extract external pack loading logic.
- [x] **Fix Caching**: Remove IO from `_detect_project_type_cached`.
- [x] **Stabilize Tests**: Fix `test_tech_skills.py` to not rely on repo artifacts.

### Nice to Have Soon
- [ ] **Renderer Registry**: Refactor `generate_skills` to use a strategy pattern for output formats.
- [ ] **Config Validation**: Use Pydantic to validate `config.yaml` structure on load.
- [ ] **Logging**: Replace `click.echo` with standard `logging` in library modules (keep `click.echo` in `main.py` only).

### Future / Scaling
- [ ] **Remote Packs**: Support `git` URLs directly in `--include-pack` to fetch skills without manual cloning.
- [ ] **Plugin System**: Allow third-party Python packages to register new Detectors and Importers.

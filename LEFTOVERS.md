# LEFTOVERS — Dead Code Inventory

Dead code identified by **vulture 2.14** on 2026-03-28, verified manually.
Items are grouped by type. Each entry records *what it was*, *why it was likely created*, and *last known git context* so you can restore anything if needed.

All items confirmed unused: no callers found in `generator/`, `cli/`, or `prg_utils/`.

---

## Entire Dead Files

These files have **zero imports** across the codebase. They can be deleted whole.

### `generator/analyzers/validator.py` (146 lines)
**What:** Validation helpers — `ValidationResult`, `validate_project_data()`, `validate_generated_content()`, `check_markdown_syntax()`.
**Likely origin:** Early quality-checking scaffold, predates `ContentAnalyzer` / `QualityReport` which took over that role.
**Last touched:** commit `6cbf829` (generic "fix").
**Safe to delete:** Yes.

---

### `generator/rules_manager.py` (90 lines)
**What:** `RulesManager` — a facade intended to mirror `SkillsManager` for the rules pipeline.
**Likely origin:** Symmetry effort: since `SkillsManager` exists, someone started `RulesManager`. The rules pipeline uses `RulesGenerator` directly; the facade was never wired up.
**Last touched:** commit `6cbf829`.
**Safe to delete:** Yes.

---

### `generator/integrations/ide_registry.py` (117 lines)
**What:** `IDERegistry` — detects IDE type (cursor, vscode, cline, antigravity), symlinks config files, registers rules.
**Likely origin:** Planned abstraction for multi-IDE support. The actual IDE handling is inline in `analyze_cmd.py` (`--ide` flag). This registry was never plugged in.
**Last touched:** commit `5d4f1e0`.
**Safe to delete:** Yes. If multi-IDE support expands, the logic would be rebuilt from `analyze_cmd.py`.

---

### `generator/analyzers/llm_analyzer.py` (35 lines)
**What:** `analyze_with_llm()` — scaffold for optional LLM deep analysis.
**Likely origin:** Future-feature placeholder. The function body is `# TODO: Implement` and returns input unchanged.
**Last touched:** commit `096ac58` (merge commit).
**Safe to delete:** Yes. It's a TODO stub that was never implemented.

---

### `generator/quality_loop.py` (224 lines)
**What:** `batch_improve_with_feedback()` — iterative quality improvement loop using `ContentAnalyzer` + `ThreadPoolExecutor`.
**Likely origin:** Quality feedback loop feature (commit `29d990b` "feat: quality feedback loop (90+/100 guaranteed)", then `247f3a3` "Optimize with ThreadPoolExecutor"). The loop was built, then the feature path that called it was removed or replaced.
**Last touched:** commit `247f3a3`.
**Safe to delete:** Yes. The underlying `ContentAnalyzer.analyze()` it called still exists and is used directly.

---

## Dead Code in Active Files

These are unused classes, methods, or variables inside files that are otherwise live. Safer to clean up individually.

### `generator/config.py` — `PlannerConfig` dataclass (lines 39–57)
**What:** Config dataclass for `ProjectPlanner` (AI tokens, README limits, phase counts).
**Likely origin:** Created to centralize planner settings. `ProjectPlanner` never reads from it — it uses hardcoded values (`max_tokens=3000`).
**Active part of file:** `AnalyzerConfig` (lines 6–35) IS used by `ContentAnalyzer`.
**Action:** Delete lines 39–57 only.

---

### `generator/config.py` — `AnalyzerConfig` unused fields (lines 11–14, 20–22, 26–28, 33)
**What:** `low_score_threshold`, `excellent_threshold`, `good_threshold`, `needs_improvement_threshold`, `ai_temperature`, `ai_max_tokens`, `patch_max_tokens`, `max_content_length`, `max_readme_excerpt`, `max_suggestions`, `total_default_score`.
**Likely origin:** `ContentAnalyzer` was refactored to use hardcoded thresholds instead of reading from config.
**Note:** The `AnalyzerConfig` class itself is instantiated in `ContentAnalyzer.__init__`, so keep the class — just be aware the individual fields are unused.
**Action:** Low priority — the fields are harmless dataclass defaults.

---

### `generator/exceptions.py` — 4 unused exception classes
**What:** `AIClientError`, `SecurityError`, `PlanParsingError`, `ConfigurationError`.
**Likely origin:** Defined upfront for a structured error hierarchy. The codebase instead raises `RuntimeError` and `ValueError` everywhere.
**Active part of file:** `PRGError` base class (line 5) — keep.
**Action:** Delete the 4 unused subclasses.

---

### `prg_utils/exceptions.py` — 2 unused exception classes
**What:** `TemplateNotFoundError`, `DetectionFailedError`.
**Likely origin:** Same pattern — defined for future use, never raised.
**Active part of file:** `ProjectRulesGeneratorError`, `READMENotFoundError`, `AIProviderError`, `SkillGenerationError` — check before deleting.
**Action:** Delete `TemplateNotFoundError` and `DetectionFailedError` only.

---

### `generator/strategies/base.py` — `SkillGenerationStrategy` Protocol
**What:** Protocol defining the `generate()` interface for all strategy classes.
**Likely origin:** Proper type-safe strategy pattern. Strategies were later written without importing this Protocol (they match it structurally / duck-typing).
**Note:** Deleting won't break runtime, but removing the Protocol loses the explicit interface contract. Consider keeping as documentation.
**Action:** Optional. If you want to re-enforce the contract, import it in each strategy. Otherwise delete.

---

### `generator/skill_creator.py` — 4 dead methods

| Method | Lines | Notes |
|--------|-------|-------|
| `generate_all()` | ~122 | Batch skill generation — replaced by `SkillsManager.generate_all()` |
| `setup_symlinks()` | ~292 | Symlink management — now in `SkillPathManager` |
| `_detect_from_dependencies()` | ~635 | Consolidated into `utils/tech_detector.py` (comment in tech_detector confirms this) |
| `_detect_from_readme()` | ~641 | Same — consolidated into `tech_detector.py` |

---

### `generator/content_analyzer.py:335` — `_parse_analysis_response()`
**What:** Private method that parses LLM response text into a dict. Never called — `ContentAnalyzer` builds its report from heuristics, not LLM output.
**Action:** Delete method.

---

### `generator/outputs/clinerules_generator.py:147` — `generate_clinerules_with_inline()`
**What:** Alternative generator that embeds skills inline into the rules file.
**Likely origin:** Experimented with inline format, went back to separate files.
**Action:** Delete function.

---

### `generator/readme_generator.py:48` — `generate_readme_interactively()`
**What:** Interactive CLI prompts for README generation.
**Likely origin:** Early interactive mode that was replaced by `--from-readme` flag.
**Action:** Delete function.

---

### `generator/rules_creator.py:246` — `GIT_ANTIPATTERNS` dict
**What:** Hardcoded mapping of git anti-pattern messages. The method that was meant to use it now builds antipatterns dynamically from git log output.
**Action:** Delete the dict literal.

---

### `generator/utils/trigger_evaluator.py` — 3 items

| Item | Line | Notes |
|------|------|-------|
| `triggers_found` variable | ~35 | Set but never read in `extract_triggers()` |
| `evaluate()` method | ~47 | Instance method, never called — static `extract_triggers()` is used instead |
| `auto_test_cases()` method | ~89 | Test data generator for triggers, never called |

---

### `generator/planning/project_planner.py:199` — `generate_task_plan()`
**What:** Generates a task-level implementation plan for a query string.
**Likely origin:** Planned to be called from a CLI command that was never wired up.
**Note:** `generate_roadmap()` on the same class IS used. Keep the class.
**Action:** Delete `generate_task_plan()` method.

---

### `generator/skill_discovery.py:319` — `resolve_active_skills()`
**What:** Returns skills whose triggers match a query string — a trigger-based lookup.
**Likely origin:** For auto-activating skills from user messages. Not wired into the CLI flow.
**Action:** Delete method.

---

### `generator/skill_parser.py:72` — `build_triggers()`
**What:** Builds a trigger dict from a parsed skill. Never called — trigger logic moved to `TriggerEvaluator`.
**Action:** Delete method.

---

### `generator/skill_templates.py:73,86` — `get_tech_skills()`, `get_core_skills()`
**What:** Return lists of skill names filtered by tech or marked as core. Never called by CLI or other modules.
**Action:** Delete both functions.

---

### `generator/storage/skill_paths.py` — 3 dead methods
**What:** `get_learned_skill()`, `list_learned_skills()`, `list_builtin_skills()` — path resolution helpers.
**Likely origin:** Public API for a skill browser/lister that was never built. Skills are currently discovered via glob in `SkillDiscovery`.
**Action:** Delete all three.

---

### `generator/skills/enhanced_skill_matcher.py` — 3 dead methods
**What:** `get_skill_name_for_tech()`, `get_skill_triggers()`, `list_all_tech_categories()`.
**Likely origin:** Rich API for skill matching — the class was expanded but only `match_skills_for_tech()` is actually called.
**Action:** Delete the three unused methods.

---

### `generator/incremental_analyzer.py:201` — `needs_regeneration()`
**What:** Checks if content needs to be regenerated based on file changes.
**Likely origin:** Planned incremental-mode feature. `IncrementalAnalyzer` is used in `analyze_cmd.py`, but only `analyze()` and `should_skip()` — not this method.
**Action:** Delete method.

---

### `generator/templates.py` — `load_template()`, `get_rules_template()`, `get_core_skills()` (lines 9, 150, 155)
**What:** YAML template loaders.
**Note:** `get_skills_template()` (line 100) IS called from `SkillTemplates.get_template()`. Only `load_template`, `get_rules_template`, and `get_core_skills` are dead.
**Action:** Delete the three unused functions.

---

## Summary

| Category | Count | Lines saved (est.) |
|----------|-------|-------------------|
| Entire dead files | 5 | ~611 |
| Dead classes in active files | 4 | ~80 |
| Dead methods/functions in active files | ~18 | ~250 |
| Dead variables/constants | ~5 | ~30 |
| **Total** | **~32 items** | **~970 lines** |

## Removal Order (safest first)

1. Entire dead files (no callers, low blast radius)
2. Dead exception classes (isolated, no tests depend on them)
3. Dead methods in `skill_creator.py` (already superseded by `tech_detector.py`)
4. Remaining dead methods (one file at a time, run `pytest` after each)

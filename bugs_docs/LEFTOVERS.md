# LEFTOVERS — Dead Code Inventory

> **Status: RESOLVED** — All items removed or confirmed already gone as of 2026-03-28.
> 546 tests passing, 11 skipped after cleanup.

Dead code identified by **vulture 2.14** on 2026-03-28, verified manually.

---

## Entire Dead Files — ALL GONE

| File | Lines | Disposition |
|------|-------|-------------|
| `generator/analyzers/validator.py` | 146 | Already deleted before this inventory |
| `generator/rules_manager.py` | 90 | Already deleted |
| `generator/integrations/ide_registry.py` | 117 | Already deleted |
| `generator/analyzers/llm_analyzer.py` | 35 | Already deleted |
| `generator/quality_loop.py` | 224 | Already deleted |
| `generator/strategies/base.py` | ~30 | Deleted this session (unused Protocol) |

---

## Dead Code in Active Files — ALL RESOLVED

| Item | File | Disposition |
|------|------|-------------|
| `PlannerConfig` dataclass | `generator/config.py` | Already gone |
| `AIClientError`, `SecurityError`, `PlanParsingError`, `ConfigurationError` | `generator/exceptions.py` | Already gone |
| `TemplateNotFoundError`, `DetectionFailedError` | `prg_utils/exceptions.py` | Already gone |
| `GIT_ANTIPATTERNS` dict | `generator/rules_creator.py` | Removed this session |
| `triggers_found` variable | `generator/utils/trigger_evaluator.py` | Removed this session |
| `evaluate()`, `auto_test_cases()` | `generator/utils/trigger_evaluator.py` | Already gone |
| `generate_clinerules_with_inline()` | `generator/outputs/clinerules_generator.py` | Removed this session |
| `generate_readme_interactively()` | `generator/readme_generator.py` | Removed this session (+ ghost test) |
| `get_tech_skills()`, `get_core_skills()` | `generator/skill_templates.py` | Removed this session |
| `load_template()`, `get_rules_template()`, `get_core_skills()` | `generator/templates.py` | Removed this session |
| Dangling `@staticmethod` decorator | `generator/skill_parser.py` | Fixed this session |
| `generate_all()`, `setup_symlinks()`, `_detect_from_dependencies()`, `_detect_from_readme()` | `generator/skill_creator.py` | Already gone |
| `_parse_analysis_response()` | `generator/content_analyzer.py` | Already gone |
| `generate_task_plan()` | `generator/planning/project_planner.py` | Already gone |
| `resolve_active_skills()` | `generator/skill_discovery.py` | Already gone |
| `build_triggers()` | `generator/skill_parser.py` | Already gone |
| `get_learned_skill()`, `list_learned_skills()`, `list_builtin_skills()` | `generator/storage/skill_paths.py` | Already gone |
| `get_skill_name_for_tech()`, `get_skill_triggers()`, `list_all_tech_categories()` | `generator/skills/enhanced_skill_matcher.py` | Already gone |
| `needs_regeneration()` | `generator/incremental_analyzer.py` | Already gone |

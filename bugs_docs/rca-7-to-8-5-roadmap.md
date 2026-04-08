# Root Cause Analysis: 7.0 → 8.5 Roadmap

Source: Second-pass review (SECOND_PASS_REVIEW.md), April 2026.

---

## Three Architectural Root Causes

**RC-1: Feature accumulation into a single command surface**
Every feature was added as a flag to `analyze()` rather than a distinct sub-command. The function
has 33 parameters serving 6+ orthogonal use cases. Partial extraction to helpers/pipeline modules
reduced line count but not complexity — `analyze()` is still the traffic controller.

**RC-2: Silent degradation as the default failure mode**
Broad `except Exception` catches throughout the codebase allow the pipeline to continue on failure
while hiding the root cause from users. Users cannot distinguish "good path" from "fallback path."
Key offenders: `_phase_enhanced_parse`, `READMEStrategy.generate()`, `cowork_strategy.py` (×5).

**RC-3: Discipline tools treated as advisory**
black, isort, and mypy were defined in CI but the code was not clean enough to pass them. Every
PR could ship with formatting drift and type errors because the gates had no teeth.

---

## Prioritized Action Plan

### P0 — Establish the Non-Negotiable Baseline

#### P0-A: Make black + isort + mypy blocking in CI — ✅ COMPLETE (2026-04-08)

All three tools were already defined as steps in `.github/workflows/ci.yml`. The blocking gate
became real only after the code was brought into compliance (see P0-B below and the
black/isort/mypy cleanup in this session). The CI now enforces:
- `black --check .`
- `isort --profile black --check-only .`
- `mypy generator/ cli/ prg_utils/ --ignore-missing-imports`

Files changed to reach compliance:
- `cli/analyze_helpers.py` — resolved `Optional[str]` return type; widened `List[str]` → `Sequence[Union[str, Path]]`
- `cli/ralph_cmd.py` — removed stale `# type: ignore[type-arg]`
- `prg_utils/git_ops.py` — widened `stage_files` and `commit_files` params from `List` → `Sequence`
- `cli/feature_cmd.py`, `cli/analyze_pipeline.py` — auto-formatted by black
- `tests/test_analyze_cmd_characterization.py`, `tests/test_cov_agent_cmd.py`,
  `tests/test_cov_cmd_review.py`, `tests/test_cov_providers_cmd.py`,
  `tests/test_pipeline_characterization.py`, `tests/test_cov_create_rules_cmd.py`,
  `tests/test_cov_jobs.py` — auto-formatted by black
- `tests/test_cov_agent_plan_helpers.py`, `tests/test_cov_create_rules_cmd.py`,
  `tests/test_cov_pure_logic.py` — fixed by isort

#### P0-B: Fix all mypy errors — ✅ COMPLETE (2026-04-08)

Errors resolved:
1. `analyze_helpers.py:204` — `detect_provider()` returns `Optional[str]`; collapsed to `str` via `or ""`
2. `analyze_helpers.py:232` — `List[str]` passed to `commit_files(List[Union[str, Path]])`;
   fixed by widening both the parameter type and `commit_files`/`stage_files` to `Sequence`
3. `ralph_cmd.py:20` — stale `# type: ignore[type-arg]` removed

Result: `mypy generator/ cli/ prg_utils/ --ignore-missing-imports` → **0 errors in 134 files**.

---

### P1 — Replace Silent Degradation with Visible Failure Modes

#### P1-A: Distinguish "skipped" from "failed" in `_phase_enhanced_parse` — ✅ COMPLETE (2026-04-08)

`analyze_pipeline.py`: narrowed `except Exception` → `(OSError, ValueError, RuntimeError)`.
Warning moved from verbose-gated to unconditional stderr. `AttributeError` (programming error)
now propagates — bugs surface instead of being silently swallowed.
Locked in by `test_enhanced_parse_warning_emitted_regardless_of_verbose` and
`test_enhanced_parse_attribute_error_propagates` in `tests/test_p1_visible_failures.py`.

#### P1-B: Apply same pattern to READMEStrategy and CoworkStrategy — ✅ COMPLETE (2026-04-08)

- `readme_strategy.py`: narrowed to `(ImportError, OSError, ValueError, TypeError, AttributeError)`
- `cowork_strategy.py`: 4 of 6 catches narrowed with specific types; 2 intentionally broad
  catches (creator factory, AI call) documented with `# noqa: BLE001` + reason comment
- 10 new tests in `tests/test_p1_visible_failures.py`

#### P1-C: Decompose `analyze()` by splitting sub-commands — ✅ COMPLETE (2026-04-08)

`analyze()` reduced from 33 → 19 parameters. 14 flags extracted to focused commands:

| Removed flags | New command |
|---|---|
| `--create-skill`, `--add-skill` | `prg skills create` |
| `--remove-skill` | `prg skills remove` |
| `--generate-index` | `prg skills index` |
| `--quality-check`, `--eval-opik`, `--auto-fix`, `--max-iterations` | `prg quality` (new `cli/quality_cmd.py`) |
| `--create-rules`, `--rules-quality-threshold` | `prg create-rules` (already existed) |
| `--from-readme`, `--force`, `--scope` | moved to `prg skills create` |

`SkillsManager` promoted to module-level import in `skills_cmd.py` for test patchability.
Tests updated: `test_analyze_cmd_characterization.py`, `test_skills_manager.py`.

---

### P2 — Consistency and Maintenance Debt

#### P2-A: `providers_cmd.py` — replace `print()` in fallback branches — ✅ COMPLETE (2026-04-08)

5 `print()` calls in two `except ImportError` blocks replaced with `click.echo()`.
Files: `cli/providers_cmd.py` (lines 81-86, 211-213).

#### P2-B: Eliminate `_get_enhanced_context` double-parse — ✅ COMPLETE (2026-04-08)

`analyze_pipeline.py` was re-instantiating `EnhancedProjectParser` inside `_build_unified_content`
via `_get_enhanced_context`, even though Phase 1 already produced `enhanced_context`.
Fix: added `enhanced_context` parameter to `_build_unified_content`; updated call site to thread
the value through; deleted `_get_enhanced_context`. EnhancedProjectParser is now constructed
exactly once per pipeline run.

#### P2-C: `DesignGenerator` fallback — replace 200+ line template with minimal stub — ✅ COMPLETE (2026-04-08)

`generator/design_generator.py`: `_generate_comprehensive_template` (220 lines of
cache/auth-specific heuristics) replaced with an 8-line honest stub that returns a minimal
`Design` with the original request as the title and a note that an AI provider is required.
Tests updated: `test_design_generator.py::test_generate_fallback` (criterion changed from
`len(success_criteria) >= 1` to asserting the "AI provider unavailable" note),
`test_two_stage_planning.py::test_design_with_real_project` (assertion relaxed to
`"authentication" in d.title.lower()`).

#### P2-D: `SelfReviewer` — scope hallucination detection correctly — ✅ COMPLETE (2026-04-08)

- `generator/planning/self_reviewer.py`: `_detect_hallucinations` → `_flag_suspicious_terms`;
  `ReviewReport.hallucinations` field → `suspicious_terms`;
  `to_markdown()` section header `"## Hallucinations Detected"` → `"## Suspicious Terms"`
- `cli/cmd_review.py`: display labels updated to "Suspicious Terms"
- Tests updated in `test_cov_pure_logic.py` and `test_cov_cmd_review.py`

---

## Score Tracker

| Milestone | Score | Date |
|---|---|---|
| First pass | 6.8/10 | 2026-04-06 |
| Second pass (packaging fixed) | 7.0/10 | 2026-04-08 |
| P0 complete (baseline enforced) | ~7.4/10 | 2026-04-08 |
| P1 complete (visible failures + decomposition) | ~8.0/10 | 2026-04-08 |
| P2 complete (consistency + debt) | ~8.5/10 | 2026-04-08 |

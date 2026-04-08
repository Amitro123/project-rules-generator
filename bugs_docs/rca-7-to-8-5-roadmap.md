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

#### P1-A: Distinguish "skipped" from "failed" in `_phase_enhanced_parse` — ⬜ TODO

`analyze_pipeline.py:208-213`: catches bare `Exception`, emits warning only under `--verbose`,
returns `None` for both "incremental skip" and "parse failure" cases. Fix:
- Narrow catch to `(OSError, ValueError, RuntimeError)`
- Emit warning unconditionally to stderr (not verbose-gated)
- Differentiate None-by-design (incremental) from None-by-error at call sites

#### P1-B: Apply same pattern to READMEStrategy and CoworkStrategy — ⬜ TODO

- `readme_strategy.py:148`: broad catch silently returns `None` on parser bugs
- `cowork_strategy.py`: 5 broad catches; at minimum add `# noqa: BLE001` with explanation
  for each that is genuinely non-fatal

#### P1-C: Decompose `analyze()` by splitting sub-commands — ⬜ TODO

The real fix is sub-commands, not more helper extraction:

| Current flags | Target sub-command |
|---|---|
| `--quality-check`, `--eval-opik`, `--auto-fix` | `prg quality` |
| `--create-rules` | `prg rules` |
| `--generate-index` | `prg skills index` |
| Core generation | `prg analyze .` (≤12 params) |

Skill management flags (`--create-skill`, `--remove-skill`, `--list-skills`) already have
`prg skills` equivalents — remove the aliases from `analyze`.

---

### P2 — Consistency and Maintenance Debt

#### P2-A: `providers_cmd.py` — replace `print()` in fallback branches — ✅ COMPLETE (2026-04-08)

5 `print()` calls in two `except ImportError` blocks replaced with `click.echo()`.
Files: `cli/providers_cmd.py` (lines 81-86, 211-213).

#### P2-B: Eliminate `_get_enhanced_context` double-parse — ⬜ TODO

`analyze_pipeline.py:413-420` re-instantiates `EnhancedProjectParser` after Phase 1 already ran it.
Fix: thread the `enhanced_context` from `_phase_enhanced_parse` through to `_build_unified_content`
directly and delete `_get_enhanced_context`.

#### P2-C: `DesignGenerator` fallback — replace 200+ line template with minimal stub — ⬜ TODO

`generator/design_generator.py` (671 lines) contains `_generate_comprehensive_template` —
a deterministic pseudo-architect. Replace with a 10-line honest stub.

#### P2-D: `SelfReviewer` — scope hallucination detection correctly — ⬜ TODO

Rename detection method from `detect_hallucinations()` to `flag_suspicious_terms()` and update
`ReviewReport` field names to reflect the actual (lint-style, not semantic) detection scope.

---

## Score Tracker

| Milestone | Score | Date |
|---|---|---|
| First pass | 6.8/10 | 2026-04-06 |
| Second pass (packaging fixed) | 7.0/10 | 2026-04-08 |
| P0 complete (baseline enforced) | ~7.4/10 | 2026-04-08 |
| P1 complete (silent degradation fixed) | ~7.8–8.1/10 | — |
| P2 complete (consistency + debt) | ~8.5/10 | — |

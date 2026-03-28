
  ---
  I'm working on **Project Rules Generator (PRG)** — a Python CLI tool (`prg`)
  that analyzes a project and generates `.clinerules/` rules, skills, and plans
  for AI agents (Claude, Cursor, Windsurf, Gemini).

  Repo: https://github.com/Amitro123/project-rules-generator
  Working dir: C:\Users\Dana\.gemini\antigravity\scratch\project-rules-generator
  Current version: v0.2.0 (just shipped)
  Tests: ~530 passing, 11 skipped, 3 flaky (TestFromDesign — live LLM calls, pre-existing)

  ## What we just completed (v0.2.0)

  - `generator/base_generator.py` — NEW `ArtifactGenerator` ABC, shared
    strategic-depth contract (pain-first, WHY-before-HOW, skip-consequence)
  - `CoworkRulesCreator`, `TaskDecomposer`, `SkillGenerator` all inherit it
  - `generator/tech_registry.py` — single source of truth for all tech metadata
  - `_check_strategic_depth()` in quality_checker.py — penalises shallow artifacts
  - Skill prompt rules 9-11: pain-first Purpose, WHY per step, pain-named description
  - Fixed: `.env` colon-syntax parsing (`GEMINI_API_KEY:'value'` now works)
  - Fixed: AI failure now shows red warning; stub fallback shows yellow warning
  - Fixed: skill topic name hallucinated as package name (pytest-debugger bug)

  ## What to tackle this session (priority order)

  1. **Flaky tests** — `tests/test_task_decomposer.py::TestFromDesign` (3 tests)
     call `TaskDecomposer(api_key=None)` which still picks up `GOOGLE_API_KEY`
     from env and makes live Gemini calls. Should be mocked so they're deterministic.

  2. **Stub placeholder detection** — `StubStrategy` output with `[bracket
     placeholders]` scores 90 because `validate_quality()` doesn't penalise
     unfilled placeholders. Add detection in `quality_checker.py`.

  3. **Auto-trigger count bug** — `validate_quality()` counts 0 triggers when
     they're listed in `## Auto-Trigger` prose instead of the frontmatter
     `triggers:` list. Parser needs to read both locations.

  4. **`SubTask.skip_consequence` tests** — the new field has no dedicated tests.
     Add tests for `_parse_response()` extracting `SkipConsequence:` and
     `generate_plan_md()` rendering `**Skip consequence:**`.

  5. **Version display verbosity** — `prg analyze` prints
     `Project Rules Generator v0.2.0` on every run; consider `--verbose` only.

  ## Key architecture
  - Strategy chain: AIStrategy → READMEStrategy → CoworkStrategy → StubStrategy
  - Quality gate threshold: score ≥ 70 (was 90, lowered for strategic depth penalties)
  - Gemini workaround: `export GEMINI_MODEL=gemini-2.5-flash-lite` (separate quota)
  - Provider key: `GOOGLE_API_KEY` set in env; `GEMINI_API_KEY` reads from .env

  Please start with item 1 (flaky tests) — read the test file first before making changes.

  ---
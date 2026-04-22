# CHANGELOG

All notable changes to this project will be documented in this file.

---

## [Unreleased]

### Pre-open-source hardening (Batches A–D + OSS audit)

**Packaging**
- Moved `templates/` → `generator/templates/` so Jinja templates ship inside the wheel. `pip install project-rules-generator` now works end-to-end; previously loaders 404'd on packaged templates. (#1)
- Added `generator/py.typed` (PEP 561) — downstream projects now see inline type hints. (#11)
- `.env.example` now documents every API-key env var the code reads (`GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPIK_API_KEY`, plus optional model overrides). (#10)

**Skill quality (Batch D)**
- `validate_quality()` now parses the three real trigger shapes (list, list-of-dicts, and `auto_triggers: {keywords, project_signals}` dict) via a `_flatten_trigger_spec()` helper. Previously 9 real skills in the repo silently crashed scoring with `TypeError: unsupported operand type(s) for +: 'dict' and 'list'`.
- Templates emit `description: |` as a multi-line block scalar with one `When …` line per trigger, so the scorer's "lacks When trigger phrase" check actually finds them.
- `allowed-tools` emitted as a YAML list instead of a quoted string.
- Broadened `_PAIN_INDICATORS` to match real pain-oriented phrasing (`tedious`, `error-prone`, `brittle`, `stale`, `out of sync`, etc.); previously 69% of generated skills were falsely penalised.
- Description now checked for length (< 40 chars penalised) and leading/trailing whitespace (template-fill leak).

**Concurrency & durability (Batches B/C)**
- All skill writes go through atomic temp-file + `os.replace` so interrupted runs never leave half-written `SKILL.md` files.
- Cross-platform file locking (`fcntl` / `msvcrt`) on the skill-tracker manifest — concurrent `prg analyze` runs no longer corrupt it.
- Placeholder-leak detector (`contains_unfilled_placeholders`) added; quality gate warns before writing placeholder content to `learned/`.

**Skill generator hygiene (Blocker #3)**
- `SkillGenerator.create_skill()` refuses names starting with `temp-`, `tmp-`, `scratch-`, `placeholder-`, or `draft-` — scratch files like `temp_test_project-workflow` can never ship.
- Underscores / spaces normalise to hyphens (so `temp_foo` is caught, not collapsed to `tempfoo`).
- 14 new tests in `tests/test_skill_name_refusal.py`.

**Documentation**
- `CONTRIBUTING.md` documents canonical skill shape, frontmatter schema, and naming rules. (#8)
- `docs/AUTHORING-SKILLS.md` — deep-dive skill-authoring guide with worked examples. (#14)
- `README.md` Quick Start now mentions `clean.ps1` for Windows housekeeping. (#12)
- `docs/PRE-OSS-AUDIT.md` tracks all 19 audit findings with a Progress Log.

**Repo cleanup**
- Removed tracked developer scratch files (`CR.md`, `leftovers.md`, `temp_test_project-workflow.md`) and stale generated artefacts (`.clinerules/clinerules.yaml`, `.clinerules/rules.md`).
- Deduped duplicate learned skills — `fastapi-api/` → `fastapi-endpoints/`, `gitpython/` → `gitpython-ops/`, `pytest/` + `pytest-patterns/` → `pytest-best-practices/`, `python-cli/` → `python-cli-patterns/`. Canonical shape is now `<slug>/SKILL.md` directory form only.
- `.gitignore` extended with scratch-file patterns.

**Metrics**
- Test suite: **1367 → 1381** (+14 refusal tests), all green.
- Generated-skill mean quality score: **67 → ≥ 90** on a 10-skill sample.
- End-to-end CLI flows (`prg analyze --create-skill` and `prg create-rules`) both score 100/100.

---

## [v0.3.0] — 2026-04-03

### Published to PyPI

Package is now available on PyPI as `project-rules-generator`.

```bash
pip install project-rules-generator
```

Previously required cloning the repository and running `pip install -e .`. That workflow remains available for contributors.

PyPI page: https://pypi.org/project/project-rules-generator/

### New command: `prg watch`

Watches project files and automatically runs `prg analyze --incremental` whenever they change.

**Monitored files:** README.md, pyproject.toml, requirements*.txt, Dockerfile, docker-compose.yml, package.json, Cargo.toml, go.mod, and all files under `tests/` directories.

**Behaviour:**
- 2-second debounce coalesces rapid saves into a single run
- Re-entry guard prevents overlapping analysis runs
- Graceful Ctrl+C shutdown

**Usage:**
```bash
prg watch [PATH] [--delay 2.0] [--ide cursor] [--quiet]
```

### New dependency

`watchdog>=3.0.0` — installed automatically with the package.

### Skill usage tracking

Every `prg agent` skill match now silently increments a persistent usage counter. Two new sub-commands let users record feedback and surface chronically unhelpful skills.

**Data file:** `~/.project-rules-generator/skill-usage.json` — accumulates across all projects and sessions.

**New module:** `generator/skill_tracker.py`
- Thread-safe `SkillTracker` class backed by `skill-usage.json`
- Tracks `match_count`, `useful` / `not_useful` vote totals, composite `score` (0.0–1.0), and `last_used` timestamp
- Auto-called on every `prg agent` match — no user action required
- `get_low_scoring(threshold=0.3)` returns skills below threshold that have ≥ 3 feedback votes

**New commands:**

`prg skills feedback <skill-name> --useful` | `--not-useful`
- Records a vote for the named skill
- Prints the updated score and vote breakdown
- Example: `Recorded: 'pytest-testing-workflow' marked as useful. Score: 75% (3 useful / 1 not useful / 8 matches)`

`prg skills stale [--threshold 0.3]`
- Lists skills scoring below the threshold (default 30%) with ≥ 3 feedback votes
- Shows score, vote counts, and match count per skill
- Suggests `prg analyze . --create-skill <name>` to regenerate each flagged skill

**End-to-end flow:**
1. `prg agent "fix the failing tests"` → skill matched → `match_count` incremented automatically
2. After using the skill: `prg skills feedback pytest-testing-workflow --useful`
3. Over time: `prg skills stale` shows which skills are consistently unhelpful
4. Regenerate: `prg analyze . --create-skill pytest-testing-workflow`

### Tests

**Total: 706 passing**

---

## [Unreleased] — 2026-04-03

### 🏁 CR #3 — Clean Pass
Every issue from [CR #2](docs/CR-3-clean-pass.md#what-was-fixed-since-cr-2) is now resolved. This is the first fully green run across all three reviews.

- **bugs_docs/**: Fully removed from git index and disk; added to `.gitignore`.
- **PRIORITIES truncation**: Fixed with two-stage fallback (line-boundary snap → full content).
- **API Key reliability**: `TaskDecomposer` and `prg review` now handle missing keys gracefully.
- **Logger integration**: `design_generator.py` raw prints converted to logging.
- **Test suite**: 650 passed, 0 failed.

Detailed report: [CR-3-clean-pass.md](file:///c:/Users/Dana/.gemini/antigravity/scratch/project-rules-generator/docs/CR-3-clean-pass.md)

---

## [Unreleased] — 2026-03-30

#### `generator/skill_creator.py`: 1190 → 824 LOC (−31%)

Three focused helper modules extracted:

| New module | LOC | Responsibility |
|---|---|---|
| `generator/skill_doc_loader.py` | 149 | Supplementary doc discovery + key-file loading for LLM context |
| `generator/skill_metadata_builder.py` | 287 | Trigger generation, tool selection, tags, YAML frontmatter rendering |

`SkillQualityValidator` extracted then consolidated (see below).

#### `generator/rules_creator.py`: 864 → 622 LOC (−28%)

Three focused helper modules extracted:

| New module | LOC | Responsibility |
|---|---|---|
| `generator/rules_git_miner.py` | 127 | Git history analysis — hot spots + large-commit detection |
| `generator/rules_renderer.py` | 111 | rules.md content rendering + anti-pattern appending |

`RulesQualityValidator` extracted then consolidated (see below).

#### `generator/quality_validators.py` — NEW (consolidated)

`SkillQualityValidator` and `RulesQualityValidator` merged into one file instead of two separate modules, since both are quality-validation concerns:

```
generator/quality_validators.py
  ├── SkillQualityValidator   — hallucination detection, auto-fix
  └── RulesQualityValidator   — completeness, conflicts, priority checks
```

Shared low-level checks remain in `generator/utils/quality_checker.py`.

#### Known Issues documented

`docs/KNOWN-ISSUES.md` created, recording 4 bugs found in `prg design` / `prg plan`:
- Success Criteria section generates empty bullets
- `prg plan` generates only 1 subtask (under-decomposed)
- Hallucinated file paths (`src/` instead of `generator/`)
- Task content truncated mid-sentence

---

## [v0.2.2] — 2026-03-28

### ✨ Features

#### `--scope` flag for `--create-skill` — explicit skill placement control

**Files:** `generator/skill_generator.py`, `generator/skills_manager.py`, `cli/analyze_cmd.py`

Added `--scope [learned|builtin|project]` option to `prg analyze --create-skill`.
Routing logic corrected to match intent:

| Command | Old behaviour | New behaviour |
|---------|--------------|---------------|
| `prg analyze . --create-skill X` | wrote to `project/` | writes to `learned/` (global, reusable) |
| `prg analyze .` (README flow) | wrote to `learned/` | writes to `project/` (project-specific) |
| `prg analyze . --create-skill X --scope builtin` | n/a | writes to `builtin/` (universal patterns) |
| `prg analyze . --create-skill X --scope project` | n/a | writes to `project/` explicitly |

**Why:** `--create-skill` is explicit human intent to capture reusable knowledge → `learned/`.
The README auto-flow produces project-context-aware content → `project/`.

---

## [v0.2.1] — 2026-03-28

### 🐛 Bug Fixes & Test Coverage

#### FIX-1 — `TestFromDesign` flaky tests (live Gemini calls)
**File:** `tests/test_task_decomposer.py`

`TestFromDesign` created `TaskDecomposer(api_key=None)` but `__init__` still picked up
`GOOGLE_API_KEY` / `GEMINI_API_KEY` from the environment, causing live API calls and
non-deterministic results.

Fix: added `@pytest.fixture(autouse=True)` to `TestFromDesign` that patches
`TaskDecomposer._call_llm` to return `""`, forcing the deterministic
`_tasks_from_design` fallback path. Tests run in ~0.3 s regardless of env state.

---

#### FIX-2 — `StubStrategy` output passed the quality gate with score 90
**File:** `generator/utils/quality_checker.py`

The existing bracket-placeholder check used a narrow list of 5 specific prefixes
(`[describe`, `[example`, `[your`, `[add`, `[insert`). `StubStrategy` generates 8+
unfilled placeholders (`[One sentence: ...]`, `[First step]`, `[Second step]`,
`[description]`, `[What artifact...]`, `[What NOT to do]`, `[What to do instead]`) that
none of those prefixes matched. Score stayed at 90 — above the 70 pass threshold.

Fix: added a general bracket-placeholder detector after the specific list. It strips
frontmatter and code blocks, then matches `[5+ chars]` not followed by `(` (excludes
markdown links and code syntax like `Dict[str, int]`). Each unique unfilled placeholder
deducts -5 points, capped at -25. `StubStrategy` output now scores ~65 (fails gate).

---

#### FIX-3 — Auto-trigger count: 0 when triggers are plain bullet items
**File:** `generator/utils/quality_checker.py`

`_extract_body_triggers()` only matched `**bold**` phrases. Skills using plain bullet
lists (e.g. `systematic-debugging/SKILL.md`: `- User reports: "bug", "error", ...`)
returned 0 triggers → -10 score penalty despite 3+ triggers being present.

Additionally, body triggers were skipped entirely when YAML `triggers:` had any entries
(`if not yaml_triggers else []`), meaning the two sources were never merged.

Fix:
- `_extract_body_triggers()` now falls back to plain `- bullet` extraction when no bold
  phrases are found.
- Merge logic changed to always read both sources:
  `metadata_triggers = list(dict.fromkeys(yaml_triggers + body_triggers))`

---

#### FIX-4 — `SubTask.skip_consequence` field lacked dedicated tests
**File:** `tests/test_task_decomposer.py`

The `skip_consequence` field added in v0.2.0 had no tests verifying its extraction or
rendering. `_parse_response()` could silently stop reading `SkipConsequence:` and
`generate_plan_md()` could drop `**Skip consequence:**` without any test failing.

Added 5 tests:
- `TestParseResponse.test_parse_skip_consequence_extracted` — field populated from LLM response
- `TestParseResponse.test_parse_skip_consequence_empty_when_absent` — defaults to `""`
- `TestParseResponse.test_parse_skip_consequence_multiple_tasks` — extracted per-task independently
- `TestGeneratePlanMd.test_plan_skip_consequence_rendered` — `**Skip consequence:**` rendered when set
- `TestGeneratePlanMd.test_plan_skip_consequence_omitted_when_empty` — line absent when field empty

---

#### FIX-5 — `prg analyze` printed version banner on every run
**File:** `cli/analyze_cmd.py`

`--verbose/--quiet` defaulted to `True`, causing the `Project Rules Generator v0.2.0`
banner (and provider info, target path) to appear on every `prg analyze` invocation.

Fix: changed default to `False`. Diagnostic output (banner, target, provider) is now
`--verbose` only. Meaningful action output (skill creation, rules saved, errors) was
already unconditional and is unaffected.

---

### 🧪 Tests

| Test class | Tests added | Covers |
|---|---|---|
| `TestBracketPlaceholderDetection` | 7 | FIX-2: clean skill no false-positive, specific stub patterns, full StubStrategy fails gate, code-block immunity, markdown link immunity, per-item penalty scaling |
| `TestAutoTriggerParsing` | 5 | FIX-3: plain bullets, bold bullets, yaml+body merge, no-trigger penalty preserved, systematic-debugging exact format |
| `TestParseResponse` | 3 | FIX-4: skip_consequence extracted, empty default, per-task independence |
| `TestGeneratePlanMd` | 2 | FIX-4: rendered when set, omitted when empty |

**Total: 547 passing, 11 skipped** (up from 530 before this session)

---

## [v0.2.0] — 2026-03-28

### Strategic Depth Pipeline (v1.5 architecture)

All PRG artifact generators now enforce a shared "pain-first, why-before-how" contract.
Every generated skill, rule set, and plan must identify the reader's broken state before
prescribing action, and explain WHY before HOW for each step.

#### `ArtifactGenerator` base class — `generator/base_generator.py` (NEW)

Abstract base class inherited by all three generators. Contributes:

- `_PAIN_FIRST_PREAMBLE` — LLM prompt fragment: pain → prescription order
- `_WHY_RULE_FORMAT` — LLM prompt fragment: `DO: X | WHY: Y` single-line format
- `_SKIP_CONSEQUENCE_FORMAT` — LLM prompt fragment: per-task `SkipConsequence:` line
- `format_rule_with_why(rule, why)` — static helper producing `"X — Y."` annotation
- `validate_depth(content)` — runs strategic-depth quality gate on any artifact
- `_build_prompt()` — abstract, forces every subclass to embed the preamble

#### `CoworkRulesCreator` refactored — `generator/rules_creator.py`

- Now inherits `ArtifactGenerator`
- `_build_prompt()` extracted; embeds `_PAIN_FIRST_PREAMBLE` + `_WHY_RULE_FORMAT`
- Rule parser updated: splits `DO: X | WHY: Y` and calls `format_rule_with_why()`
- Removed inline 160-line `TECH_RULES` dict → imports from `tech_registry.py`

#### `TaskDecomposer` refactored — `generator/task_decomposer.py`

- Now inherits `ArtifactGenerator`
- `SubTask` Pydantic model gains `skip_consequence: str = ""` field
- `_build_prompt()` embeds `_PAIN_FIRST_PREAMBLE` + `_SKIP_CONSEQUENCE_FORMAT`
- `_parse_response()` extracts `SkipConsequence:` from LLM output
- `generate_plan_md()` renders `**Skip consequence:** ...` when field is set

#### `SkillGenerator` refactored — `generator/skill_generator.py`

- Now inherits `ArtifactGenerator`
- `_build_prompt()` delegates to `skill_generation.build_skill_prompt()` (rules 9-11 already embedded)
- Removed inline 47-line `TECH_SKILL_NAMES` dict → imports from `tech_registry.py`

#### Strategic depth quality gate — `generator/utils/quality_checker.py`

New `_check_strategic_depth(content)` function penalises shallow artifacts:

- `-15` if `## Purpose` opens with `"This skill / This generates / Automatically..."`
- `-10` if `## Purpose` contains no pain indicators (`"without"`, `"prevents"`, `"every time you"`, ...)
- `-5` if Process steps have no prose reasoning before commands

Calibrated so existing high-quality skills (score ≥ 90) remain unaffected.

#### Skill generation prompts — `generator/prompts/skill_generation.py`

Added CRITICAL rules 9-11:
- Rule 9: Purpose MUST open with reader's pain — never `"This skill"`
- Rule 10: Every Process step needs one WHY sentence before the command
- Rule 11: Frontmatter `description` must name who has what pain and how it's resolved

#### `tech_registry.py` — consolidated tech metadata (v1.4 carry-over completed)

All four caller files updated to import from `tech_registry.py`:
- `skill_generator.py` — `TECH_SKILL_NAMES`
- `skill_creator.py` — `TECH_TOOLS`
- `rules_creator.py` — `TECH_RULES`
- `tech_detector.py` — `PKG_MAP`, `TECH_README_KEYWORDS`

No more duplicate tech dictionaries anywhere in the codebase.

#### README rewritten — `README.md`

Pain-first structure: opens with the developer's broken state ("Every AI agent starts knowing nothing about your project"), not feature descriptions. Added `## License` section.

#### Docs updated — `docs/architecture.md`

- Core components table updated (new `base_generator.py` row, v1.5 statuses)
- Strategic Depth Hierarchy ASCII diagram added
- `quality_checker.py` section updated with `_check_strategic_depth()` details
- Strategic Depth Contract table added (pain-first / WHY-before-HOW / skip-consequence)
- Directory Structure updated (`base_generator.py`, `tech_registry.py`, `readme_bridge.py`)

#### Builtin skill removed

`.clinerules/skills/builtin/readme-improver.md` — deleted. Content was shallow and feature-first; replaced by live AI generation via `prg analyze . --create-skill readme-improver --ai`.

---

## [v1.4] — 2026-03-28

### ✨ New Commands

#### `prg init` — First-Run Wizard
**File:** `cli/init_cmd.py`

New entry-point command that was documented in README and `docs/cli.md` but missing from the codebase. Detects tech stack, checks API key availability, generates initial `rules.md` via the existing pipeline, sets up the skills directory structure, and prints provider-aware next steps.

```bash
prg init .            # auto-detect provider
prg init . --yes      # skip confirmation
prg init . --provider groq
```

#### `prg skills list/validate/show` — Skill Inspection Sub-Commands
**File:** `cli/skills_cmd.py`

Three sub-commands under `prg skills` that were documented in `docs/cli.md` and `docs/skills.md` but missing from the codebase.

- `prg skills list [PATH] [--all]` — tabular view of all skills with layer, trigger count, tools, and frontmatter status
- `prg skills validate <NAME_OR_PATH> [PATH]` — runs `validate_quality()`, prints score/issues/warnings, exits 1 on failure
- `prg skills show <NAME_OR_PATH> [PATH]` — pretty-prints frontmatter as structured table and body as-is; accepts skill name (resolved via SkillsManager) or file path

---

### 🔧 Fixes & Improvements

#### Version: single source of truth
**File:** `cli/_version.py` (new)

Removed 6 hard-coded `"0.1.0"` strings across `cli/cli.py`, `cli/agent.py`, `cli/analyze_cmd.py`. Version is now read from `importlib.metadata` (source: `pyproject.toml`) at runtime. Fallback to `"0.1.0"` if package is not installed.

#### Python version inconsistency fixed
README badge and Prerequisites section corrected from `3.11+` to `3.8+`, matching `pyproject.toml` (`requires-python = ">=3.8"`).

#### CLI help text: `--ai` flag no longer says "requires GEMINI_API_KEY"
Updated to "requires an API key — any supported provider".

#### `detect_provider()` now recognises `GOOGLE_API_KEY` as Gemini alias
**File:** `cli/utils.py`

Auto-detection checked `GEMINI_API_KEY` only. Now also checks `GOOGLE_API_KEY` so users with the Google SDK env var get Gemini selected automatically.

#### Skill routing fixed
**Files:** `generator/skill_generator.py`

- `create_skill()` (invoked by `--create-skill`) now writes to `skills/project/` (project-specific, highest priority)
- `generate_from_readme()` (invoked by README auto-flow) now writes to `skills/learned/` (reusable, medium priority)

Previously the two paths were swapped, causing project-specific skills to land in the global learned cache and README-derived skills to be treated as project-local overrides.

#### Quality checker is now self-sufficient
**File:** `generator/utils/quality_checker.py`

`validate_quality()` now auto-parses YAML frontmatter and `## Auto-Trigger` sections when `metadata_triggers` / `metadata_tools` are not passed explicitly. Previously all callers had to extract and pass these manually; missing them caused a guaranteed −20 point penalty. All 22 project skills now score 90–100.

#### Strategy chain improvements
- **READMEStrategy**: Added relevance check — returns `None` when skill name words don't appear in the extracted project purpose, preventing README content from being echoed into unrelated skill names
- **CoworkStrategy**: Returns `None` immediately when `use_ai=False` (previously ran Jinja2 extraction, producing garbage without an LLM)
- **StubStrategy**: Now emits complete YAML frontmatter scaffold instead of a near-empty placeholder

#### Provider wiring: `design`, `plan`, `autopilot`, `manager`
**Files:** `cli/agent.py`, `cli/autopilot_cmd.py`, `cli/manager_cmd.py`, `generator/task_decomposer.py`

The `--provider` flag was accepted but silently ignored in these four commands. Fixed:
- `TaskDecomposer` refactored from Gemini-only (google.genai SDK) to shared `create_ai_client` factory; accepts `provider` param
- `design` command passes `provider=provider` to `DesignGenerator`
- `plan` command passes `provider=provider, api_key=api_key` to `TaskDecomposer`
- `autopilot` and `manager` `--provider` choices expanded from `["gemini", "groq"]` to all four providers

#### `GOOGLE_API_KEY` alias: full coverage
Fixed across `ai_strategy_router.py`, `providers_cmd.py`, `design_generator.py`, `task_decomposer.py`, `cli/utils.py` — Gemini is detected/used with either `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

#### Import-time side effects removed
**Files:** `cli/cli.py`, `cli/analyze_cmd.py`, `cli/agent.py`

`load_dotenv()` was executing 3× at import time across these modules. `sys.path.insert()` was also running at import time (unnecessary with `pip install -e .`). Both moved into `main()` / removed.

---

#### H1 — `_detect_tech_stack` deduplicated
**File:** `generator/rules_creator.py`

Removed the 70-line local `_detect_tech_stack` and `_detect_from_files` methods. `rules_creator.py` now delegates to `generator.utils.tech_detector.detect_tech_stack()` — the same function `skill_creator.py` already used. The `enhanced_context` merge is preserved as an optional post-step.

#### M6 — Builtin sync consolidated into `SkillPathManager`
**Files:** `generator/skill_discovery.py`, `generator/storage/skill_paths.py`

`SkillDiscovery.ensure_global_structure()` was reimplementing the builtin sync inline (unconditional `shutil.copytree`). Replaced with a single delegation to `SkillPathManager.ensure_setup()`, which uses mtime comparison to avoid unnecessary copies. Also fixed a pre-existing `parents=True` omission in `SkillPathManager.ensure_setup()` that caused test failures on fresh directories.

#### M7 — `find_readme()` centralised
**File:** `generator/utils/readme_bridge.py` (new public function)

Four different inline README discovery loops existed across the codebase with slightly different filename lists. Added `find_readme(project_path: Path) -> Optional[Path]` to `readme_bridge.py` with a single canonical candidate order. Updated 6 callers:
- `generator/incremental_analyzer.py`
- `generator/parsers/enhanced_parser.py` (2 locations)
- `generator/project_analyzer.py`
- `generator/rules_generator.py`
- `cli/analyze_cmd.py`
- `cli/init_cmd.py`

---

### 🧪 Tests

- 30 new tests in `tests/test_provider_wiring.py` (TaskDecomposer, DesignGenerator, autopilot/manager provider choices)
- 15 new tests in `tests/test_init_and_skills_cmd.py` (init command, skills list/validate/show)
- **Total: 530 passing, 11 skipped**

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

# Project Roadmap: Project Rules Generator

> Last synced with codebase: 2026-04-03

---

## Phase 1: Feature Development ✅ Done

**Implement core features to generate smarter, context-aware `.clinerules`**

- [x] Task 1: Implement Context Awareness
  - [x] 1.1: Read README & Structure (`generator/analyzers/readme_parser.py`, `EnhancedProjectParser`)
  - [x] 1.2: Integrate Architecture docs — reflected in `docs/architecture.md`

- [x] Task 2: Develop Memory System (basic cross-project reuse)
  - [x] 2.1: `LearnedSkillsSource` — saves/loads skills across projects via `~/.project-rules-generator/learned/`
  - [x] 2.2: Incremental updates — `IncrementalAnalyzer` + `prg analyze . --incremental`
  - [ ] **Open**: True feedback/learning loop — skills do not improve based on usage yet

- [x] Task 3: Skill Type Generation
  - [x] 3.1: Expert skills via `CoworkSkillCreator` (AI-powered, quality-gated at 90+)
  - [x] 3.2: Basic stub skills for all 40+ techs in `TECH_SKILL_NAMES`

---

## Phase 2: Git Integration and Constitution ✅ Done

**Integrate with Git and generate constitution documents**

- [x] Task 1: Auto-commits with smart `.gitignore` handling
- [x] Task 2: Constitution Document (`prg analyze . --constitution`)
- [x] Task 3: Smart `.clinerules.yaml` exclusions + incremental mode

---

## Phase 3: Evolution and Stability 🔄 Partially Done

- [ ] Task 1: Evolution System — **NOT IMPLEMENTED** (no feedback loop or usage scoring)
- [x] Task 2: Context Awareness (full `EnhancedProjectParser`, 3-layer skill resolution)
- [x] Task 3: Bug Fixes (Issues #17, #18, #27, #30+; 650 tests passing as of 2026-04-03)

---

## Phase 4: Documentation and Maintenance 🔄 Partially Done

- [x] Task 1: Architecture Docs (`docs/architecture.md`, `docs/ARCHITECTURE_IMPROVEMENTS.md`)
- [x] Task 2: README updated (providers, skill routing, Python version)
- [ ] Task 3: `analyze_cmd.py` modularisation — still 1100+ lines (tracked as H4 in ARCHITECTURE_IMPROVEMENTS.md)

---

## Recent Work (2026-04-03 session)

### Completed

| Item | Details |
|---|---|
| **CR #3 Clean Pass** | All issues from CR #2 resolved; 650/650 tests green. |
| PRIORITY truncation fix | Two-stage fallback for codebase scanning. |
| API Key robustness | Defensive normalization in `TaskDecomposer` and `prg review`. |
| Logger migration | Removed raw `print()` from `design_generator.py`. |
| Skill routing fixed | `--create-skill` → `skills/project/`; README flow → `skills/learned/` |
| Quality checker auto-parse | `validate_quality()` now parses YAML frontmatter itself; all 22 skills score 90-100 |
| Strategy chain improved | READMEStrategy: relevance check prevents README echoing; CoworkStrategy: returns None when `use_ai=False`; StubStrategy: full YAML frontmatter scaffold |
| GOOGLE_API_KEY alias | Gemini accepts either `GEMINI_API_KEY` or `GOOGLE_API_KEY` across all entry points |
| Provider wiring (design/plan) | `--provider` flag now wired through `design`, `plan`, `autopilot`, `manager` commands |
| TaskDecomposer refactored | Replaced google.genai SDK with shared `create_ai_client` factory; accepts `provider` param |
| Import-time side effects removed | `load_dotenv()` and `sys.path.insert` moved out of module scope into `main()` |
| Version single source of truth | `cli/_version.py` via `importlib.metadata`; removed 6 hard-coded `"0.1.0"` strings |
| Python version fixed | README badge + prerequisites corrected from `3.11+` to `3.8+` (matches `pyproject.toml`) |
| CLI help text corrected | `--ai` flag no longer says "requires GEMINI_API_KEY" |
| `utils.py` GOOGLE_API_KEY | `detect_provider()` auto-detection now checks `GOOGLE_API_KEY` as Gemini alias |
| 29 new tests | `test_provider_wiring.py` — covers TaskDecomposer, DesignGenerator, autopilot/manager provider choices |
| `prg skills` sub-commands | `list`, `validate`, `show` — documented in cli.md, **not yet implemented** (see Open Items) |
| `prg init` command | Documented as recommended starting point in README + cli.md, **not yet implemented** (see Open Items) |
| H1: `_detect_tech_stack` consolidated | `rules_creator.py` local copy removed; now delegates to `tech_detector.detect_tech_stack()` |
| M6: Builtin sync consolidated | `SkillDiscovery.ensure_global_structure()` now delegates to `SkillPathManager.ensure_setup()`; fixed `parents=True` bug |
| M7: `find_readme()` added | Single discovery function in `readme_bridge.py`; 6 callers updated across `generator/` and `cli/` |

---

## Open Items (as of 2026-03-28)

### P1 — Documented but Not Implemented (user-facing gaps)

| Item | Priority | Notes |
|---|---|---|
| `prg init` command | ✅ Done | Implemented in `cli/init_cmd.py`; 7 tests |
| `prg skills list/validate/show` | ✅ Done | Implemented in `cli/skills_cmd.py`; 8 tests |

### P2 — Architecture Quick Wins (low risk, see ARCHITECTURE_IMPROVEMENTS.md)

| Item | Est. Effort | Risk |
|---|---|---|
| M5: Fix dangling `@classmethod` decorators in `skill_paths.py` | ✅ Already clean | — |
| M3: Deduplicate `README_MIN_WORDS` (2 copies) | ✅ Already clean | — |
| H1: Delete `_detect_tech_stack` copies; delegate to `tech_detector` | ✅ Done | — |
| M6: Consolidate builtin sync into `SkillPathManager` | ✅ Done | — |
| M7: Add `find_readme()` to `readme_bridge.py` | ✅ Done | — |
| M2: Replace `click.echo`/`print()` with `logging` in generator layer | ✅ Done | `workflow.py`, `project_manager.py` decoupled; `readme_generator.py` and `autopilot.py` kept (genuine interactive UI) |

### P3 — Architecture Major Work (plan separately)

| Item | Est. Effort | Risk |
|---|---|---|
| H2: `tech_registry.py` — consolidate 7 tech dictionaries | ✅ Done | — |
| H3: `skill_creator.py` God Object — split into triggers/signals/metadata modules | 2–3 days | High |
| H4: `analyze_cmd.py` God Object — extract `AnalyzePipeline` | 2–3 days | High |
| CLI-to-library coupling — `ProjectManager` uses `CliRunner` internally | 2 days | High |

### P4 — Quality / Testing

| Item | Priority |
|---|---|
| Stale docs: `autopilot-architecture.md` uses `prg copilot`/`prg lifecycle` (should be `prg autopilot`/`prg manager`) | Medium |
| Stale docs: `v1.1-features.md` uses `from src.` imports | Low |
| Unit tests for `SkillDiscovery`, `SkillPathManager`, `EnhancedSkillMatcher` | Medium |
| `except Exception:` audit — replace broad catches with specific types | Medium |
| Evolution / feedback loop (skills improve with usage) | Low |

---

## Future Strategy: Taking PRG to the Next Level 🚀

A comprehensive strategy for the next phase of development has been established, focusing on distribution, live-mode automation, and ecosystem integration.

**Detailed Strategy Guide:** [Next Level Strategy](file:///c:/Users/Dana/.gemini/antigravity/scratch/project-rules-generator/docs/NEXT-LEVEL-STRATEGY.md)

### 🔝 Priority Tiers

| Tier | Focus Area | Key Features |
|---|---|---|
| **Tier 1** | High Impact | **PyPI Publishing**, **`prg watch`** (live mode), Evolution System (Learning), IDE Extension |
| **Tier 2** | Ecosystem | GitHub Actions, Multi-file Context (ADRs, Architecture), LiteLLM integration, MCP Server |
| **Tier 3** | Debt/Cleanup | Specific Exception handling, God-object decomposition (`analyze_cmd.py`) |

**Immediate Next Step:** Prepare for PyPI publishing and implement `prg watch`.

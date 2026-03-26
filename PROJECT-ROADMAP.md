# Project Roadmap: Project Rules Generator

> Last synced with codebase: 2026-03-24

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
  - [x] 1.1: `.gitignore` exclusions via `prg_utils/git_ops.py`
  - [x] 1.2: Auto-commit on `prg analyze` (default `--commit`)

- [x] Task 2: Constitution Document
  - [x] 2.1: `constitution.md` generated via `generate_constitution()` + `prg analyze . --constitution`
  - [x] 2.2: Architecture docs at `docs/architecture.md`

- [x] Task 3: Smart `.clinerules.yaml` exclusions
  - [x] 3.1: Context-aware YAML via `generate_clinerules()` in `generator/outputs/`
  - [x] 3.2: Incremental mode avoids regenerating unchanged sections

---

## Phase 3: Evolution and Stability 🔄 Partially Done

**Continuously improve the AI's performance and fix bugs**

- [ ] Task 1: Evolution System — **NOT IMPLEMENTED**
  - [ ] 1.1: "Gets smarter every usage" — no feedback loop or usage scoring exists yet
  - [ ] 1.2: Memory integration for evolution — `LearnedSkillsSource` stores, but doesn't update based on quality feedback

- [x] Task 2: Context Awareness (enhanced)
  - [x] 2.1: Full `EnhancedProjectParser` with dependency parsing, test pattern detection
  - [x] 2.2: Architecture integration via `SkillDiscovery` + 3-layer resolution

- [x] Task 3: Bug Fixes and Stability (Issues #17, #18, #27)
  - [x] 3.1: Issue #17 — 5 bugs fixed; Issue #18 — 6 bugs + design fixes; 400+ tests passing
  - [x] 3.2: Dual path managers unified (DESIGN-1), dead prompt builder removed (DESIGN-2)

---

## Phase 4: Documentation and Maintenance 🔄 Partially Done

**Maintain and document the project for future development**

- [x] Task 1: Architecture Docs
  - [x] 1.1: `docs/architecture.md` with ASCII diagrams and Strategy Pattern explained

- [x] Task 2: README and Documentation
  - [x] 2.1: Feature descriptions updated through v1.4.1 (AI Router, 4 providers)

- [ ] Task 3: Ongoing Maintenance
  - [x] 3.1: `CHANGELOG.md` tracks changes per version
  - [ ] 3.2: `analyze_cmd.py` still 1100+ lines — further modularisation in progress

---

## Open Items (as of 2026-03-24)

| Item | Priority | Status |
|---|---|---|
| Evolution / feedback loop (skills improve with usage) | High | Not started |
| `analyze_cmd.py` generation block split into sub-modules | Medium | In progress |
| Unit tests for `SkillDiscovery`, `SkillPathManager`, `EnhancedSkillMatcher` | Medium | Not started |
| Autopilot stability — `AutopilotOrchestrator` implemented but not battle-tested | Low | Exists, needs testing |

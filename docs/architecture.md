# PRG Architecture

## Overview

PRG generators share a common strategic-depth contract via `ArtifactGenerator`.
Every generated artifact — rules, plans, skills — must identify the reader's pain
before prescribing action, and explain WHY before HOW for each step or rule.

## Core Components

| File | Role | Status |
|------|------|--------|
| `generator/base_generator.py` | **Base** - `ArtifactGenerator` ABC, strategic-depth contract | ✅ NEW (v1.5) |
| `generator/rules_creator.py` | **Rules** - `CoworkRulesCreator(ArtifactGenerator)` — orchestrator (622 LOC) | ✅ Refactored |
| `generator/rules_git_miner.py` | **Rules/Git** - Hot-spot + large-commit detection | ✅ NEW |
| `generator/rules_renderer.py` | **Rules/Render** - rules.md content + anti-pattern appending | ✅ NEW |
| `generator/task_decomposer.py` | **Plans** - `TaskDecomposer(ArtifactGenerator)` | ✅ Refactored (v1.5) |
| `generator/skills_manager.py` | **Facade** - Single entry point for all skill operations | ✅ Active |
| `generator/skill_generator.py` | **Skills** - `SkillGenerator(ArtifactGenerator)`, Strategy Pattern | ✅ Refactored (v1.5) |
| `generator/skill_creator.py` | **Cowork Intelligence** - High-quality skill generation — orchestrator (824 LOC) | ✅ Refactored |
| `generator/skill_doc_loader.py` | **Skills/Docs** - Supplementary doc discovery + key-file loading | ✅ NEW |
| `generator/skill_metadata_builder.py` | **Skills/Metadata** - Triggers, tools, tags, frontmatter rendering | ✅ NEW |
| `generator/quality_validators.py` | **Quality** - `SkillQualityValidator` + `RulesQualityValidator` | ✅ NEW |
| `generator/skill_parser.py` | **Parser** - Extracts data from skill files | ✅ Active |
| `generator/skill_templates.py` | **Templates** - Loads YAML skill templates | ✅ Active |
| `generator/tech_registry.py` | **Tech Registry** - Single source for all tech metadata | ✅ NEW (v1.4) |
| `generator/utils/tech_detector.py` | **Tech Detection** - Consolidated tech stack detection | ✅ NEW (v1.1) |
| `generator/utils/quality_checker.py` | **Quality/Shared** - Strategic-depth + format validation (base checks) | ✅ Refactored (v1.5) |

## Architecture Diagram

### Strategic Depth Hierarchy (v1.5)

```
ArtifactGenerator (ABC)                    generator/base_generator.py
─────────────────────────────────────────────────────────────────────
_PAIN_FIRST_PREAMBLE    : str   "describe what BREAKS without this rule/step..."
_WHY_RULE_FORMAT        : str   "DO: <rule> | WHY: <one sentence consequence>"
_SKIP_CONSEQUENCE_FORMAT: str   "SkipConsequence: <what breaks if task omitted>"
─────────────────────────────────────────────────────────────────────
+ format_rule_with_why(rule, why) → str     [static]  "X — Y."
+ validate_depth(content) → QualityReport              calls quality gate
# _build_prompt(*args, **kwargs) → str       [abstract] enforces the contract
         △                    △                    △
         │                    │                    │
CoworkRulesCreator      TaskDecomposer        SkillGenerator
──────────────────      ──────────────        ──────────────
_build_prompt()         _build_prompt()       _build_prompt()
  preamble +              preamble +            delegates to
  _WHY_RULE_FORMAT         _SKIP_              skill_generation.
_generate_rules_          CONSEQUENCE_        build_skill_prompt()
  via_llm()               FORMAT               (rules 9-11 embedded)
  parses WHY from       _parse_response()
  "DO: X | WHY: Y"       extracts
  via format_rule_        skip_consequence
  _with_why()           generate_plan_md()
                          renders
                          **Skip consequence:**
```

### Skills Pipeline (v1.1+)

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI / User Interface                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    SkillsManager (Facade)                    │
│  • create_skill()  • list_skills()  • extract_all_triggers() │
└───────┬──────────────────┬──────────────────┬───────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│SkillDiscovery│  │SkillGenerator│  │ SkillParser  │
│              │  │(ArtifactGen) │  │              │
│• list_skills │  │• create_skill│  │• parse_skill │
│• resolve     │  │  (Strategy)  │  │• extract     │
└──────────────┘  └───────┬──────┘  └──────────────┘
                          │
                          ▼
        ┌─────────────────┴─────────────────┐
        │         Strategy Pattern           │
        ▼                                   ▼
┌──────────────┐                  ┌──────────────────┐
│  Strategies  │                  │CoworkSkillCreator│
│              │                  │                  │
│• AIStrategy  │                  │• Pain-first goals│
│• READMEStrat │◄─────────────────│• WHY per step    │
│• CoworkStrat │  (uses)          │• Quality gates   │
│• StubStrat   │                  │• Jinja2 template │
└──────────────┘                  └──────────────────┘
        │                                   │
        └──────────────┬────────────────────┘
                       │ both use
                       ▼
              ┌──────────────────┐
              │  generator/utils │
              │                  │
              │• tech_detector   │
              │• quality_checker │◄── _check_strategic_depth()
              │• readme_bridge   │    pain-first + why checks
              └──────────────────┘
```

## Strategy Pattern (v1.1)

`SkillGenerator.create_skill()` uses a chain of strategies:

1. **AIStrategy** - Uses Groq/Gemini AI providers (when `--ai` flag set)
2. **READMEStrategy** - Parses README for context (when `--from-readme` set)
3. **CoworkStrategy** - Uses `CoworkSkillCreator` intelligence (default)
4. **StubStrategy** - Generic template fallback (always available)

Complexity reduced from **D (23) → B (8)** (73% improvement).

## Utils Module (v1.1 NEW)

### `tech_detector.py`
Consolidated tech detection from `skill_creator.py` and `skill_parser.py`:
- `detect_tech_stack(project_path, readme)` - Full detection pipeline
- `detect_from_dependencies(project_path)` - From requirements.txt/package.json
- `extract_context(tech, readme)` - Extract README lines mentioning a tech

### `quality_checker.py`
Consolidated quality checking from `skill_generator.py` and `skill_creator.py`:
- `is_stub(filepath, project_path)` - Check if skill is a generic stub
- `validate_quality(content, triggers, tools)` - Full quality report with strategic depth
- `_check_strategic_depth(content)` - NEW (v1.5): penalises shallow artifacts
  - `-15` if Purpose opens with "This skill / This generates / Automatically"
  - `-10` if Purpose contains no pain indicators ("without", "prevents", "instead of"…)
  - `-5` if Process steps have no reasoning before commands
- `QualityReport` - Dataclass with score, issues, warnings, suggestions

## Strategic Depth Contract (v1.5)

Every PRG artifact must satisfy three requirements enforced by `ArtifactGenerator`:

| Requirement | Applies to | How enforced |
|---|---|---|
| **Pain-first Purpose** | Skills, Rules | `_check_strategic_depth()` in quality gate |
| **WHY before HOW** | Rules | `_WHY_RULE_FORMAT` in `_build_prompt()` + `format_rule_with_why()` |
| **Skip consequence** | Plan tasks | `_SKIP_CONSEQUENCE_FORMAT` in `_build_prompt()` + `SubTask.skip_consequence` |

### Why this matters

A rule without WHY is ignored. A plan task without skip-consequence is treated as optional.
A skill Purpose that opens with "This skill generates X" fails to answer the reader's
first question: *"Is this my problem?"*

**Before (shallow):**
```
DO: Use async/await for I/O operations
```

**After (strategic depth):**
```
DO: Use async/await for I/O operations | WHY: blocking the event loop stalls all concurrent requests
```
Stored as: `"Use async/await for I/O operations — blocking the event loop stalls all concurrent requests."`

## Files Removed (v1.1)

| File | Reason | Lines Saved |
|------|--------|-------------|
| `generator/skills_generator.py` | Legacy template-based approach, superseded by `SkillGenerator` | 107 |
| `generator/skill_matcher.py` | Unused - functionality covered by `SkillDiscovery` | 151 |

**Total: 258 lines removed, 2 files eliminated**

## Complexity Metrics

| Method | Before | After | Grade |
|--------|--------|-------|-------|
| `SkillGenerator.create_skill()` | 23 (D) | 8 (B) | ✅ 73% reduction |
| `SkillGenerator._is_generic_stub()` | 15 | 1 (delegates) | ✅ Eliminated |
| `SkillParser.extract_tech_context()` | 20 | 1 (delegates) | ✅ Eliminated |
| `CoworkSkillCreator._detect_tech_stack()` | 18 | 3 (delegates) | ✅ Eliminated |

## Skill & Rules Generation Flow (v1.2)

Full end-to-end flow for `prg analyze . --create-skill <name>` and `prg create-rules .`,
including the README sufficiency bridge introduced in v1.2.

```
prg analyze . --create-skill <name>          prg create-rules .
        │                                            │
        ▼                                            ▼
SkillGenerator.create_skill()            RulesGenerator.create_rules()
        │                                            │
        │   Strategy chain:                          │
        │   AIStrategy (if --ai)                     │
        │   → READMEStrategy (if --from-readme)      │
        │   → CoworkStrategy  ◄──────────────────────┘
        │   → StubStrategy (fallback)
        │
        ▼
CoworkStrategy.generate()
        │
        ├─ is_readme_sufficient(readme)?
        │        │ NO (< 80 words or missing)
        │        ▼
        │   bridge_missing_context()   [generator/utils/readme_bridge.py]
        │        │
        │        ├── sys.stdin.isatty()?
        │        │         │ YES (CLI)              NO (IDE / pipe / CI)
        │        │         ▼                        ▼
        │        │   Show project tree        Return project tree only
        │        │   Ask user 2-3 sentences   (AI infers from structure)
        │        │   Combine into context
        │        │
        │        └── supplement prepended to readme_content
        │
        │ YES (README sufficient) → use as-is
        │
        ▼
CoworkSkillCreator.create_skill()
        │
        ├── _load_key_files()
        │       ├── entry points (main.py, app.py, pyproject.toml ...)
        │       ├── project_tree  [_scan_project_tree()]
        │       └── supplementary docs (spec.md, SKILLS_ARCHITECTURE.md,
        │                               AMIT_CODING_PREFERENCES.md,
        │                               docs/features.md, docs/architecture.md ...)
        │
        ├── _build_metadata()  → triggers, signals, tools
        │
        └── _generate_content(use_ai=True)
                │
                ├── LLMSkillGenerator (Groq / Gemini)
                │       context: readme + tech_stack + structure + key_files
                │
                └── Jinja2 template fallback → inline template fallback
```

### readme_bridge module

`generator/utils/readme_bridge.py` — shared by both pipelines:

| Function | Purpose |
|---|---|
| `is_readme_sufficient(content, min_words=80)` | Returns False if README is missing or < 80 words |
| `build_project_tree(project_path)` | Walks project tree (max depth 3, max 60 items), excludes noise |
| `bridge_missing_context(project_path, name)` | CLI: prompt user. Non-interactive: tree only |

## Directory Structure

```
generator/
├── base_generator.py       # ArtifactGenerator ABC — strategic-depth contract (v1.5)
├── rules_creator.py        # CoworkRulesCreator(ArtifactGenerator)
├── task_decomposer.py      # TaskDecomposer(ArtifactGenerator)
├── skills_manager.py       # Facade (entry point)
├── skill_generator.py      # SkillGenerator(ArtifactGenerator) + Strategy Pattern
├── skill_creator.py        # Cowork intelligence
├── skill_parser.py         # Parser
├── skill_templates.py      # Template loader
├── skill_discovery.py      # File discovery
├── tech_registry.py        # Single source of truth for all tech metadata (v1.4)
├── strategies/             # Strategy implementations
│   ├── __init__.py
│   ├── base.py
│   ├── ai_strategy.py
│   ├── readme_strategy.py
│   ├── cowork_strategy.py
│   └── stub_strategy.py
└── utils/                  # Shared utilities
    ├── __init__.py
    ├── tech_detector.py    # Tech stack detection
    ├── quality_checker.py  # Quality validation + _check_strategic_depth()
    ├── readme_bridge.py    # README sufficiency + project tree
    ├── encoding.py         # Encoding utilities
    └── cli.py              # CLI utilities
```

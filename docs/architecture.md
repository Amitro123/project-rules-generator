# PRG Skills Architecture

## Overview

The skills system in PRG is organized into clear, single-responsibility components.
This document describes the architecture after the v1.1 cleanup.

## Core Components

| File | Role | Status |
|------|------|--------|
| `generator/skills_manager.py` | **Facade** - Single entry point for all skill operations | ✅ Active |
| `generator/skill_generator.py` | **Orchestrator** - Strategy Pattern for skill creation | ✅ Active (Refactored v1.1) |
| `generator/skill_creator.py` | **Cowork Intelligence** - High-quality skill generation | ✅ Active |
| `generator/skill_parser.py` | **Parser** - Extracts data from skill files | ✅ Active |
| `generator/skill_templates.py` | **Templates** - Loads YAML skill templates | ✅ Active |
| `generator/utils/tech_detector.py` | **Tech Detection** - Consolidated tech stack detection | ✅ NEW (v1.1) |
| `generator/utils/quality_checker.py` | **Quality** - Consolidated quality validation | ✅ NEW (v1.1) |

## Architecture Diagram

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
│              │  │              │  │              │
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
│• AIStrategy  │                  │• Smart triggers  │
│• READMEStrat │◄─────────────────│• Tool selection  │
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
              │• quality_checker │
              │• encoding        │
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
- `validate_quality(content, triggers, tools)` - Full quality report
- `QualityReport` - Dataclass with score, issues, warnings, suggestions

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

## Directory Structure

```
generator/
├── skills_manager.py       # Facade (entry point)
├── skill_generator.py      # Orchestrator (Strategy Pattern)
├── skill_creator.py        # Cowork intelligence
├── skill_parser.py         # Parser
├── skill_templates.py      # Template loader
├── skill_discovery.py      # File discovery
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
    ├── quality_checker.py  # Quality validation
    ├── encoding.py         # Encoding utilities
    └── cli.py              # CLI utilities
```

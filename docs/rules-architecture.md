# Rules Generation Architecture (v1.2)

## Overview

The rules system generates project-specific `.clinerules/rules.md` from a combination
of tech-stack intelligence, git history analysis, and LLM fallback for unknown stacks.

## Core Components

| File | Role |
|------|------|
| `generator/rules_generator.py` | **Entry point** — reads README, bridges context, delegates to creator |
| `generator/rules_creator.py` | **CoworkRulesCreator** — core intelligence: metadata, TECH_RULES, git antipatterns |
| `generator/utils/readme_bridge.py` | **Shared bridge** — README sufficiency check + project tree + interactive prompt |
| `generator/utils/tech_detector.py` | **Tech detection** — scans requirements.txt, pyproject.toml, package.json |

## Generation Flow

```
prg analyze . (or prg create-rules .)
        │
        ▼
RulesGenerator.create_rules()
        │
        ├─ _read_readme()
        │       └── README.md → readme_content (str)
        │
        ├─ is_readme_sufficient(readme_content)?   [readme_bridge.py]
        │         │ NO (< 80 words or missing)
        │         ▼
        │   bridge_missing_context()
        │         │
        │         ├── sys.stdin.isatty()?
        │         │         YES (CLI)               NO (IDE / pipe / CI)
        │         │         ▼                        ▼
        │         │   Show project tree         Return project tree only
        │         │   Ask: "Describe in 2-3 sentences"
        │         │   Combine: user_desc + tree
        │         │
        │         └── supplement prepended to readme_content
        │
        │ YES → use readme_content as-is
        │
        ▼
CoworkRulesCreator.create_rules(readme_content)
        │
        ├── 1. _build_metadata()
        │         │
        │         ├── _detect_tech_stack()
        │         │       ├── _detect_from_files()  ← requirements.txt / pyproject.toml
        │         │       ├── README scan (confirmed by files or core language)
        │         │       └── enhanced_context (always trusted)
        │         │
        │         ├── _detect_project_type()        ← fastapi → python-api, click → python-cli…
        │         ├── _identify_priority_areas()    ← rest_api_patterns, test_coverage…
        │         └── _detect_signals()             ← has_docker, has_tests, has_ci…
        │
        ├── 2. _generate_rules(metadata)
        │         │
        │         ├── recognized techs in TECH_RULES?
        │         │         │ NO (unknown stack: Rust, Go, Elixir…)
        │         │         ▼
        │         │   _generate_rules_via_llm()   ← LLM FALLBACK
        │         │         │
        │         │         ├── build_project_tree() + key files snippets + README
        │         │         ├── LLMSkillGenerator.generate_content()  (Groq / Gemini)
        │         │         ├── parse DO:/DONT: lines → Rule objects
        │         │         └── append _generate_generic_rules() to "General"
        │         │
        │         │ YES (recognized) → template path:
        │         ├── tech-specific rules from TECH_RULES dict
        │         │       ├── High   → "Coding Standards"
        │         │       ├── Medium → "Best Practices"
        │         │       └── Low    → "Recommendations"
        │         │
        │         ├── _generate_architecture_rules()   ← per project_type
        │         ├── _generate_testing_rules()        ← if pytest / jest detected
        │         └── _generate_generic_rules()        ← always appended
        │
        ├── 3. _extract_git_antipatterns()   (if git available)
        │         ├── hotspot detection (files changed > 10 times)
        │         └── large-commit detection (> 500 lines)
        │                └── → "Anti-Patterns from History" category
        │
        ├── 4. _generate_content()
        │         ├── YAML frontmatter (project, tech_stack, project_type, version)
        │         ├── Priority view: High → Medium → Low (flat, deduplicated)
        │         └── Category view: Coding Standards / Architecture / Testing / General…
        │
        └── 5. _validate_quality()
                  ├── completeness check (required sections present)
                  ├── rule count check (< 5 → warning)
                  ├── high-priority count (< 2 → warning)
                  ├── conflict detection (use X vs don't use X)
                  └── returns QualityReport(score, passed, issues, warnings)
```

## TECH_RULES Coverage

| Technology | High Rules | Medium Rules | Low Rules |
|------------|-----------|--------------|-----------|
| `fastapi`  | 4 | 4 | 2 |
| `react`    | 4 | 4 | 2 |
| `pytest`   | 3 | 3 | 2 |
| `docker`   | 3 | 3 | — |
| `asyncio`  | 3 | 3 | — |
| `sqlalchemy` | 3 | 3 | — |
| `click`    | 4 | 4 | 2 |
| `pydantic` | 3 | 3 | 1 |
| `jinja2`   | 3 | 3 | — |
| `groq`     | 3 | 3 | — |
| `gemini`   | 3 | 3 | — |

Unknown stacks (Rust, Go, Elixir, etc.) → **LLM fallback** via `_generate_rules_via_llm()`.

## LLM Fallback Path (Unknown Tech Stack)

```
metadata.tech_stack = ["rust", "actix"]  →  none in TECH_RULES
        │
        ▼
_generate_rules_via_llm(metadata, readme_content)
        │
        ├── build_project_tree()          ← real directory layout
        ├── key files: main.py / Cargo.toml / go.mod / package.json (first 400 chars)
        ├── README excerpt (600 chars)
        │
        ▼
LLMSkillGenerator.generate_content(prompt, max_tokens=600)
        │
        ▼
parse response:
  DO: <rule>    →  Rule(priority="High",  category="Coding Standards", source="llm_fallback")
  DONT: <rule>  →  Rule(priority="High",  category="Coding Standards", source="llm_fallback")
        │
        ▼
merge with _generate_generic_rules() → return rules_by_category
```

## readme_bridge Integration

`generator/utils/readme_bridge.py` — shared by rules AND skills pipelines:

| Function | Caller | Purpose |
|---|---|---|
| `is_readme_sufficient(content, min_words=80)` | `RulesGenerator`, `CoworkStrategy` | Gate check before bridging |
| `build_project_tree(path, max_depth=3, max_items=60)` | `bridge_missing_context`, `_generate_rules_via_llm` | ASCII tree, excludes noise |
| `bridge_missing_context(path, name, interactive=None)` | `RulesGenerator`, `CoworkStrategy` | CLI prompt or tree-only |

## Output: rules.md Structure

```markdown
---
project: my-project
tech_stack: [click, pydantic, pytest, groq]
project_type: python-cli
version: "2.0"
---

# my-project - Coding Rules

## Priority Areas
## Coding Standards
  ### High Priority   (tech-specific + architecture)
  ### Medium Priority (best practices)
  ### Low Priority    (recommendations)
## Rules by Category
  ### Architecture
  ### Testing
  ### General
  ### Anti-Patterns from History   (if git available)
## Tech Stack
## Project Structure   (signals)
```

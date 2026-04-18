# CLAUDE.md — Project Rules Generator

## What This Is
A Python CLI tool (`prg`) that analyzes a project and generates `.clinerules/` — coding rules and skills for AI agents (Claude, Cursor, Windsurf, Gemini). It reads README, code structure, and learned preferences to produce context-aware rules.

## Key Commands
```bash
# Install
pip install -e .

# Run CLI
prg analyze . --ide antigravity
prg create-rules .
prg analyze . --create-skill <name>

# Tests (always run after changes)
pytest
pytest --cov=generator --cov=prg_utils

# Format (must pass before commit)
black .
ruff check .
isort .
```

## Architecture
See [`docs/architecture.md`](docs/architecture.md) for full diagrams.

```
generator/
├── skills_manager.py    # Facade — single entry point for all skill ops
├── skill_generator.py   # Orchestrator — Strategy Pattern for skill creation
├── skill_creator.py     # CoworkSkillCreator — high-quality skill generation
├── skill_parser.py      # Parser — extracts data from skill files
├── skill_templates.py   # Template loader (YAML)
├── skill_discovery.py   # File discovery
├── strategies/          # AIStrategy → READMEStrategy → CoworkStrategy → StubStrategy
└── utils/
    ├── tech_detector.py     # Tech stack detection (consolidated)
    ├── quality_checker.py   # Quality validation + QualityReport dataclass
    ├── readme_bridge.py     # README sufficiency + project tree building
    └── encoding.py          # UTF-8 artifact cleanup

prg_utils/               # Shared utilities (non-generator)
cli/                     # CLI entry points
tests/                   # pytest tests (380+ passing)
```

**Strategy chain order**: AIStrategy (if `--ai`) → READMEStrategy (if `--from-readme`) → CoworkStrategy (default) → StubStrategy (fallback).

## Coding Conventions
- **Line length**: 120 (black + ruff)
- **Python**: 3.8+ compatible
- **No React** — this is a CLI tool only
- **Pydantic v2** for data models
- **Click** for CLI commands — update both decorator AND function signature when adding options
- **tqdm**: Always implement fallback with full interface (context manager) for CI environments
- **Encoding**: Clean UTF-8 artifacts with `.encode('utf-8', errors='replace').decode('utf-8')`
- **Factory functions**: Assign objects to variables before use in `setup_*` functions

## Testing Rules
- pytest coverage required; update tests when templates change
- When testing `ContentAnalyzer` file ops: pass `allowed_base_path=tmp_path`
- When testing LLM prompt functions: provide a **complete** input dict to avoid `KeyError`
- Verify mock targets against actual function signatures (no `AttributeError`)
- When removing features: immediately remove associated tests (no ghost failures)

## Important Constraints
- **Config single source of truth**: Never allow `.clinerules/clinerules.yaml` AND `.clinerules.yaml` to coexist
- **No duplicate config files** — enforce one root config only
- **`__pycache__`** must stay in `.gitignore`; use `clean.ps1` to purge
- **Quality thresholds**: Rules gate default is 85 (`create-rules --quality-threshold`, overridable); skill `validate_quality()` PASS is 70. Don't lower either without explicit instruction.
- **Naming**: Use functional names (`pytest-testing-workflow`) not abstract (`tech-patterns`)

## Key Docs
- [`docs/architecture.md`](docs/architecture.md) — full architecture with ASCII diagrams
- [`docs/features.md`](docs/features.md) — feature list
- [`CHANGELOG.md`](CHANGELOG.md) — version history
- [`PROJECT-ROADMAP.md`](PROJECT-ROADMAP.md) — planned work

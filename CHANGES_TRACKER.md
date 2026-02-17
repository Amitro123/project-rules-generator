# Changes Tracker

## v1.0.0 (Restored Stability) - 2026-02-17
🚀 **Global Learned Library (Restored)**
- **Learned Skills**: Skills created in one project are saved to `~/.project-rules-generator/learned/` and reused globally.
- **Workflow Naming**: Skills use functional names like `pytest-testing-workflow` instead of generic pattern names.
- **Symlinks**: Restored symlinking from global cache to `.clinerules/skills/project/`.

🧠 **Cowork Intelligence**
- **Smart Detection**: Detects needs based on actual project files (e.g. `pytest`, `tox`).
- **Tool Selection**: Automatically selects correct tools (e.g. `['pytest', 'coverage', 'tox']`).
- **Quality Gates**: Ensures generated skills are actionable and trigger-optimized.

🛠️ **Fixes**
- Reverted over-engineered "v2.0" complexity.
- Fixed tool validation logic.
- Restored `generate_all` core flow.


## Skills Architecture 🆕
- Implemented **3-layer architecture**: Project > Learned > Builtin.
- **Global Cache**: Skills now stored in `~/.project-rules-generator/`.
- **Symlink/Fallback**: Projects now link to global skills (or copy if permission denied).
- `skills_manager.py`: Refactored to handle global paths and priority resolution.
- `main.py`: Updated `analyze`, `create-skill`, and `list-skills` to work with new manager.

## Documentation
- `README.md`: Added "Skills Architecture" section explaining layers and priority.

## Tests
- `tests/test_skills_architecture.py`: Verified structure creation, priority logic, and aggregation.

## Bug Fixes
- `analyzer/readme_parser.py`: Fixed matching of "Features" section and implemented line-based parsing for nested lists to accurately extract top-level features.
- `tests/test_readme_parser.py`: Verified fix for nested list parsing.

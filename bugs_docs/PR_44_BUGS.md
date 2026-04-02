# Pull Request #44 Bug Summary
**Source:** https://github.com/Amitro123/project-rules-generator/pull/44
**Reviewed by:** Qodo & CodeRabbit

The following bugs and compliance issues were identified during automated code review of PR #44:

### 1. Vague Auto-Trigger Name (`.clinerules/auto-triggers.json`)
- **Severity**: 📘 Rule Violation (Maintainability)
- **Description**: The newly added auto-trigger identifier `dup-skill` is not functionally descriptive. Using a generic term (`dup` instead of `duplicate`) violates the PR Compliance requirement for descriptive skill/rule identifiers.
- **Affected File**: `.clinerules/auto-triggers.json`

### 2. Line Length Limit Exceeded (`generator/skill_project_scanner.py`)
- **Severity**: 📘 Rule Violation (Maintainability)
- **Description**: The inline assignment `readme_content = readme_path.read_text(...) if readme_path.exists() else ""` is written as a single long line, which likely exceeds the project's strict 120-character line length limit enforced by Black/Ruff formatting. It must be wrapped properly.
- **Affected File**: `generator/skill_project_scanner.py`

### 3. Learned Skill Path Resolution Mismatch
- **Severity**: 🐞 Bug (Correctness)
- **Description**: There is a structural mismatch in how skills are saved versus how they are resolved. `SkillPathManager.save_learned_skill` correctly saves learned skills into nested directories (`<category>/<name>/SKILL.md`), but the `get_skill_path()` fetch logic (and subsequent `.clinerules` generation) continues to search for flat `.md` files (`<category>/<name>.md`). This blocks newly learned skills from being successfully discovered.
- **Affected File**: `tests/test_skill_path_manager.py` (and relevant generator methods)

### 4. Confusing Preflight Check Output Text
- **Severity**: 🐞 Bug (UX / Maintainability)
- **Description**: Code modifications were made to ensure preflight correctly accepts both `rules.json` and `rules.md` (for `prg init`), but the underlying `PreflightReport.format_report()` CLI output continues to hardcode the check's display label as `rules.json`. This causes confusion and should be updated to a format-agnostic string (e.g., `Rules file` or `Project rules`).
- **Affected File**: `generator/planning/preflight.py`

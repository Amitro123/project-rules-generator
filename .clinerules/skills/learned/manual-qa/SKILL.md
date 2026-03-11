---
name: manual-qa
description: |
  Run a full manual QA pass on the project-rules-generator codebase: verify skill
  generation quality, check CLI emoji output, run the test suite, and confirm no
  regressions. Use when user mentions "manual qa", "quality check", "qa pass",
  "test run", "regression check", "verify skills". Do NOT activate for
  "general testing theory", "unit test design questions".
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  author: PRG
  version: 1.0.0
  category: testing
  tags: [qa, testing, pytest, quality, regression]
---

# Skill: Manual QA

## Purpose

Run a structured, end-to-end quality assurance pass on the project-rules-generator:
validate that skill generation produces correct output, all tests pass, CLI output
renders correctly on Windows, and no regressions are present.

## Auto-Trigger

- User mentions: "manual qa", "qa pass", "quality check"
- User asks to "verify", "validate", or "regression check" the project
- After merging a PR or applying a code review fix
- Working in: `generator/analyzers/readme_parser.py`, `generator/skill_*.py`, `cli/`

---

## Process

### 1. Run the Full Test Suite

```bash
cd c:\Users\Dana\.gemini\antigravity\scratch\project-rules-generator
pytest --tb=short -q
```

**Expected**: ≥437 passed, ≤1 pre-existing failure (`test_two_stage_planning.py::test_design_with_real_project` — known title-casing issue, do not treat as regression).

If failures beyond the known one appear → **stop and investigate before proceeding**.

---

### 2. Run Targeted CR-Fix Regression Tests

```bash
pytest tests/test_manus_cr_fixes.py tests/test_readme_parser.py tests/test_readme_to_skill_quality.py -v
```

All 40+ tests in these files must pass (exit code 0).

---

### 3. Validate Skill Generation (README Strategy)

```bash
prg analyze . --create-skill "manual-qa-test" --from-readme README.md --force
```

Then check the quality score:

```bash
python -c "
from generator.utils.quality_checker import validate_quality
from pathlib import Path
content = Path('.clinerules/skills/learned/manual-qa-test/SKILL.md').read_text(encoding='utf-8')
r = validate_quality(content)
print(f'Score: {r.score}  Passed: {r.passed}  Issues: {r.issues}')
"
```

**Expected**: Score ≥ 70, `Passed: True`, Issues empty.

---

### 4. Verify CLI Emoji Output (Windows)

```bash
prg analyze . --create-skill "emoji-check" --from-readme README.md --force 2>&1
```

**Expected output** (check for correct Unicode — NOT garbled bytes):
```
✅ Skills structure initialized (Global -> Project)
✨ Created new skill 'emoji-check' in ...
🔄 Updating agent cache...
✅ auto-triggers.json refreshed!
```

❌ **Fail** if you see `Γ£à`, `≡ƒöä`, or `Γ£¿` — the `SetConsoleOutputCP(65001)` fix in `cli/cli.py` may have been reverted.

Clean up after:
```bash
python -c "import shutil; shutil.rmtree('.clinerules/skills/learned/emoji-check', ignore_errors=True)"
```

---

### 5. Verify README Parser Improvements

Run the CR-specific parser checks inline:

```bash
python -c "
from generator.analyzers.readme_parser import extract_process_steps, extract_anti_patterns

# Fix 3: workflow section parsing
readme = '''
# Calculator
## Development Workflow
1. Create file in ops/
2. Implement calculate()
3. Add tests
4. Run pytest
## Coding Standards
- Never use global variables
- Always use type hints
'''
steps = extract_process_steps(readme)
patterns = extract_anti_patterns(readme, tech=[])

print('Steps found:', len(steps))
assert len(steps) >= 4, f'Fix 3 broken: got {steps}'

print('Anti-patterns found:', len(patterns))
assert any('global' in p.lower() for p in patterns), f'Fix 4 broken: got {patterns}'

print('PASS: Fix 3 and Fix 4 working correctly')
"
```

---

### 6. Verify pyproject.toml Package Config

```bash
python -c "
import tomllib, pathlib
data = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
pkgs = data['tool']['setuptools']['packages']
assert 'analyzer' not in pkgs, f'Fix 1 broken: analyzer still in packages: {pkgs}'
assert 'src' not in pkgs, f'Fix 1 broken: src still in packages: {pkgs}'
assert 'cli' in pkgs, f'Fix 1 broken: cli missing from packages: {pkgs}'
deps = data['project']['dependencies']
assert any('python-dotenv' in d for d in deps), f'Fix 2 broken: python-dotenv missing: {deps}'
print('PASS: pyproject.toml fixes intact')
"
```

---

### 7. Report Results

Create a summary table of each check:

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| Full suite | `pytest -q` | ≥437 passed | |
| CR regression tests | `pytest tests/test_manus_cr_fixes.py` | all pass | |
| Skill quality score | quality_checker script | ≥70 | |
| CLI emoji output | `prg analyze --create-skill` | ✅ not Γ£à | |
| Fix 3 (process steps) | inline python | ≥4 steps from Workflow | |
| Fix 4 (anti-patterns) | inline python | "global" captured | |
| pyproject.toml | inline python | cli in pkgs, python-dotenv in deps | |

---

## Output

- QA report (fill in the table above)
- List of any regressions found with file + line number
- Go/No-Go decision for release

---

## Anti-Patterns

❌ Skip Step 1 (full suite) and only run targeted tests — you'll miss cross-module regressions

❌ Accept "score: 80 / passed: True" without checking the Process section content — a score of 80 can still have generic boilerplate steps

❌ Forget to clean up test skills created during QA (`emoji-check`, `manual-qa-test`) — they pollute the learned skills cache

❌ Treat the `test_design_with_real_project` failure as a new regression — it is a known, pre-existing title-casing bug unrelated to skill generation

❌ Run QA in a virtual environment where `python-dotenv` isn't installed — always use the project venv

---

## Tech Stack Notes

- **pytest** — test runner (`pytest.ini` at project root, 51 test files, ~440 tests)
- **quality_checker** — `generator/utils/quality_checker.py`, threshold 70/100
- **prg CLI** — entry via `main.py` → `cli/cli.py` → `cli/analyze_cmd.py`
- **Windows console encoding** — `SetConsoleOutputCP(65001)` in `cli/cli.py` L7–16; must be present for emoji to render
- **Known failure** — `tests/test_two_stage_planning.py::TestDesignGeneratorIntegration::test_design_with_real_project` is pre-existing and accepted
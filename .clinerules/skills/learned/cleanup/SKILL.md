---
name: cleanup
description: |
  When the user needs to clear temporary files and build artifacts to ensure a fresh project state.
  When the user encounters inconsistent test results or unexpected build behavior due to stale cache files.
  When the user wants to reduce repository noise or prepare the project for a clean build or release.
  When the user mentions "cleanup", "clean project", "clear cache", "remove artifacts", "fresh start".
  Do NOT activate for: "clean code", "clean architecture", "refactor", "database cleanup".
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  author: PRG
  version: 1.0.0
  category: project
  tags: [cleanup, python, cache, build, testing, environment, ruff, mypy, pytest]
---

# Skill: Cleanup Project Artifacts

## Purpose

Stale `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and `dist/` directories
are a silent source of inconsistent test results, outdated type errors, and confusing linter
output in the `project-rules-generator` project. This skill removes all known build and cache
artifacts so every run starts from a verified clean state — without accidentally deleting
source code or configuration files.

## Auto-Trigger

Activate when the user mentions:
- **"cleanup"**, **"clean project"**, **"clear cache"**
- **"remove artifacts"**, **"fresh start"**, **"stale cache"**
- Before running a full `pytest` suite to rule out cache-poisoned results
- Before building or publishing a new `dist/` package

Do NOT activate for: `"clean code"`, `"clean architecture"`, `"DATABASE cleanup"`, `"refactor"`

---

## CRITICAL

- Verify the working directory is the project root before running any delete commands.
- **Never** remove `pyproject.toml`, `requirements*.txt`, `pytest.ini`, `.env`, or any source file.
- On Windows (PowerShell), `find` and `rm -rf` are not natively available — use the PowerShell equivalents shown below.
- The `dist/` directory in this project contains packaged distributions; only clean it when preparing a new release.

---

## Process

### 1. Remove Python Bytecode and `__pycache__`

Stale `.pyc` files can mask code changes since Python loads cached bytecode first.

**Linux / macOS / Git Bash:**
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

**Windows PowerShell:**
```powershell
Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
```

---

### 2. Remove pytest Cache

Stale `.pytest_cache` can cause `pytest --lf` (last-failed) to replay wrong tests.

```powershell
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
```

---

### 3. Remove Type-Checker and Linter Caches

This project uses both `mypy` and `ruff`; their caches can produce outdated diagnostics.

```powershell
Remove-Item -Recurse -Force .mypy_cache  -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .ruff_cache  -ErrorAction SilentlyContinue
```

---

### 4. Remove Build and Distribution Artifacts

Clean before a new `python -m build` run to avoid mixing stale `.whl` / `.tar.gz` files.

```powershell
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist  -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter "*.egg-info" -Directory | Remove-Item -Recurse -Force
```

---

### 5. Remove Coverage Artifacts

`.coverage` and `htmlcov/` can hold stale data that skews branch-coverage reports.

```powershell
Remove-Item -Force .coverage -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force htmlcov -ErrorAction SilentlyContinue
```

---

### 6. Validate Cleanup

Confirm all targeted paths are gone before proceeding.

```powershell
$targets = @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist", "htmlcov")
$found = $false
foreach ($t in $targets) {
    $hits = Get-ChildItem -Recurse -Filter $t -ErrorAction SilentlyContinue
    if ($hits) { Write-Host "Still present: $t"; $found = $true }
}
if (-not $found) { Write-Host "✅ Cleanup complete — no stale artifacts found." }
```

---

### 7. Verify Tests Still Pass on Clean State

```bash
pytest --tb=short -q
```

**Expected**: ≥1367 passed (the only pre-existing failure is
`tests/test_two_stage_planning.py::test_design_with_real_project` — known title-casing bug,
not a regression).

---

## Output

After a successful cleanup:
- No `__pycache__` or `.pyc` files remain in any subdirectory
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache` are gone
- `build/`, `dist/`, `*.egg-info/` are removed
- `.coverage` and `htmlcov/` are removed
- `pytest` passes the full suite from a cold cache (no tests lost to cleanup)

---

## Anti-Patterns

❌ **Don't** use `git clean -fdx` without understanding what it removes — it will also delete `.env` and other gitignored-but-critical files.
✅ **Do** use the targeted commands above, which only touch known cache/artifact directories.

❌ **Don't** delete `.venv/` unless you are explicitly rebuilding the environment — it wastes install time and can break the current shell session.
✅ **Do** keep the virtual environment intact and only rebuild it when `pip install -r requirements.txt` produces conflicts.

❌ **Don't** run cleanup mid-test-run or mid-`ruff check` — wait for active tool sessions to finish.
✅ **Do** run cleanup as a discrete step before starting a fresh analysis cycle.

❌ **Don't** skip Step 7 (re-running `pytest`) — cleanup removes the cache, so the first subsequent test run validates a true cold-cache baseline.
✅ **Do** always verify test count after cleanup to catch any cache-dependent hidden failures.

---

## Tech Stack Notes

- **pytest** — test runner; cache lives in `.pytest_cache/` (project root); config in `pytest.ini`
- **mypy** — static type checker; cache in `.mypy_cache/`; config in `pyproject.toml [tool.mypy]`
- **ruff** — linter/formatter; cache in `.ruff_cache/`; config in `pyproject.toml [tool.ruff]`
- **setuptools** — packaging; artifacts in `build/`, `dist/`, `*.egg-info/`
- **python-dotenv** — reads `.env` at project root; **never** delete `.env` during cleanup
- **Windows note** — this project runs on Windows; use PowerShell `Remove-Item` instead of `rm -rf`

---

*Regenerated using Gemini API (GEMINI_API_KEY) · PRG Cleanup Skill v1.0.0*
---
name: god-function-refactor
description: >-
  Use when user mentions "break up analyze", "god function", "oversized command",
  "split analyze_cmd", "extract services", "too many responsibilities".
  Do NOT activate for "analyze project" or "run analysis".
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
triggers:
  - "break up analyze"
  - "god function"
  - "oversized command"
  - "split command handler"
  - "extract service"
metadata:
  tags: [refactoring, architecture, maintainability]
  priority: High
---

# Skill: God-Function Refactor

## Purpose

Break up oversized CLI command handlers (god-functions) into focused service objects.
Applies the Single Responsibility Principle to commands like `cli/analyze_cmd.py`
that own config loading, provider setup, README resolution, pipeline execution,
git operations, quality checks, and more — all in one function.

## CRITICAL

> These rules are non-negotiable during every refactoring session.

- Never change public CLI behavior — only internal structure
- Always run `pytest` before AND after each extracted service
- Keep all extracted classes in the same module tree (`cli/` or `generator/`)
- Each service must have a single, named responsibility

## Auto-Trigger

Activate when the user asks to:
- "break up analyze_cmd.py"
- "split the analyze command into services"
- "reduce god-function complexity"
- "extract orchestration from CLI handler"

## Process

### 1. Measure the current hot spot

```bash
# Count lines and identify hot functions
grep -n "^def \|^class " cli/analyze_cmd.py
python -c "
import ast, sys
tree = ast.parse(open('cli/analyze_cmd.py').read())
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        print(f'  {node.name}: lines {node.lineno}-{node.end_lineno} ({node.end_lineno - node.lineno} lines)')
"
```

### 2. Identify responsibilities inside the handler

Look for these patterns in the god-function:
- Config/env loading → extract to `_load_config()`
- Provider setup → extract to `_setup_provider()`
- README resolution → extract to `_resolve_readme()`
- Analysis pipeline → delegate to `AnalysisPipeline.run()`
- Git staging/commit → delegate to `GitCommitter.commit_outputs()`
- Quality checking → delegate to `run_quality_check()`
- Rules generation → delegate to `RulesGenerator.generate()`

### 3. Extract one service at a time (safe steps)

```python
# Pattern: extract helper + keep original calling it
# Before:
def analyze(...):
    readme_path = _find_readme_path(project_path, readme)  # inline logic
    ...

# After step 1: extract to module-level helper
def _find_readme(project_path, readme_flag):
    """Resolve README path — raise ReadmeNotFoundError if missing."""
    ...

def analyze(...):
    readme_path = _find_readme(project_path, readme)  # now calls helper
    ...
```

### 4. Move helpers to dedicated modules when they accumulate

Once 3+ helpers share a theme, move them:
- `cli/analyze_helpers.py` — already exists for some helpers
- `cli/analyze_pipeline.py` — orchestration logic
- `cli/analyze_quality.py` — quality check logic (already extracted)

### 5. Verify nothing broke

```bash
pytest tests/ -x -q
black cli/analyze_cmd.py
ruff check cli/analyze_cmd.py
```

## Output

- `cli/analyze_cmd.py` reduced to option parsing + orchestration calls (< 100 lines ideal)
- New/updated helper modules each with a single clear responsibility
- All existing tests still pass

## Anti-Patterns

❌ Moving everything to one giant `AnalyzeService` class (just moves the problem)
✅ Create multiple small, named services (`ReadmeResolver`, `ProviderSetup`, etc.)

❌ Changing CLI option names or behavior during refactor
✅ Keep public interface identical — only internal structure changes

❌ Skipping tests between extractions (breaks bisect)
✅ Run `pytest -x -q` after each individual extraction

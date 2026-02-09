Fix project-rules-generator issues - consolidated:

## 1. False Tech Stack Detection (HIGH PRIORITY)
The tool detects "react, fastapi" in Python CLI projects that don't use them.
- Parse actual dependencies from requirements.txt/pyproject.toml, not just README mentions
- Verify imports exist in codebase with AST parsing
- Ignore documentation/examples that reference tech but don't import it
- Test: Should NOT detect React/FastAPI in this Python CLI project

## 2. Git Commit Path Failure (MEDIUM)
Command still fails with exit status 1 despite previous fix.
- Debug: Print the exact git command being executed
- Ensure BOTH -C flag AND file paths use Path().as_posix()
- Example: git -C "C:/path" add "C:/path/file.md" (all forward slashes)
- Test: git add/commit should work on Windows without errors

## 3. Skill Quality Improvements (MEDIUM)
Generated skills need to be more actionable:
- Remove hypothetical anti-patterns - only show real code issues found
- Add executable triggers: ["validate pydantic", "fix model defaults"]
- Include tools/dependencies section: [ruff, mypy, pytest]
- Convert vague action items to runnable commands:
check: ruff check --select ANN prg_utils/
test: pytest tests/test_config_schema.py

text

## 4. Duplicate Skills Warning (LOW)
DEBUG messages about "Skipping duplicate skill from lower priority source"
- Either prevent duplicates from being generated, or
- Silence these DEBUG logs if expected behavior

Work in order 1→2→3→4. Test after each fix.
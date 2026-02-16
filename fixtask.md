You are an AI coding assistant working on the repository `Amitro123/project-rules-generator`.

Task 1 – Fix redundant file scanning:
- Open `generator/parsers/dependency_parser.py`.
- Locate the `detect_system_dependencies` (or similarly named) function around line 377.
- Currently, it scans both `*.py` and `**/*.py`, which causes root-level Python files to be processed twice.
- Refactor the implementation so that:
  - Each Python file is only scanned once.
  - The logic for discovering Python files is clear and centralized (e.g., a single glob pattern from the project root, or a function that deduplicates paths).
  - Add or update tests (if a test suite exists) to ensure that:
    - All intended files are still scanned.
    - No file path is processed more than once.
  - Keep the public behavior and function signature backward compatible.

Task 2 – Improve PEP 508 dependency parsing:
- In `generator/parsers/dependency_parser.py`, around line 293, find the regex used to parse dependency strings.
- The current regex does not fully support PEP 508.
- Replace or extend the parsing logic so that it correctly handles:
  - Package names with extras, e.g. `pkg[extra1,extra2]`.
  - Complex version specifiers: `==`, `!=`, `<`, `<=`, `>`, `>=`, `~=`, `===`, and comma-separated ranges.
  - Optional environment markers, e.g. `; python_version < "3.10"` or `; sys_platform == "win32"`.
- You may either:
  - Implement a more complete regex-based parser, or
  - Preferably, use a well-maintained library that parses PEP 508 requirement strings (for example: `packaging.requirements.Requirement`) and adapt the code to work with it.
- Ensure the parser returns structured data compatible with the existing code (name, version specifier(s), extras, environment markers).
- Add or update tests with multiple realistic PEP 508 examples, including edge cases.

General guidelines:
- Keep the code style consistent with the rest of the project.
- Do not introduce breaking changes to the public API unless absolutely necessary.
- After implementing the changes, run the existing tests (if available) and add new ones where it improves coverage.

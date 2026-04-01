# Design: Robustness and Security Enhancements for Project Analyzer and Autopilot Orchestrator

## Problem Statement
The current codebase suffers from broad exception handling, making debugging and error recovery challenging, and uses brittle regex for task parsing. Furthermore, there's a critical lack of validation for file paths before LLMs are allowed to write, posing a significant security risk. These issues lead to an unstable, insecure, and difficult-to-maintain application, hindering its reliability and trustworthiness.

## Architecture Decisions

- **Granular Exception Handling Strategy**: Use specific exception types and centralized logging for improved error diagnosis and recovery (vs `except Exception: pass`, vs `print(e)`).
  - Pro: Enables targeted error recovery strategies.
  - Pro: Provides clear, actionable error messages to users and developers.
  - Pro: Improves application stability by preventing unexpected crashes due to unhandled specific errors.
  - Pro: Facilitates easier debugging and root cause analysis.
  - Con: Requires more verbose `try/except` blocks and careful mapping of potential errors.
  - Con: Initial implementation can be time-consuming to identify all specific error conditions.
- **Structured Task Definition using `TASKS.json`**: Replace regex-based task parsing with a standardized JSON file for defining available tasks (vs continued regex parsing, vs hardcoded task definitions in Python).
  - Pro: Enhances robustness and maintainability by decoupling task definitions from code.
  - Pro: Allows for easier extension and modification of tasks without code changes.
  - Pro: Improves readability and clarity of task specifications.
  - Pro: Enables schema validation for task definitions, preventing malformed tasks.
  - Con: Introduces an external dependency (`TASKS.json` file) that must be managed.
  - Con: Requires careful handling of JSON parsing errors if the file is malformed.
- **Strict LLM File Write Path Validation**: Implement a robust validation mechanism to restrict LLM-suggested file writes to explicitly allowed paths within the project directory (vs no validation, vs simple `os.path.abspath` check).
  - Pro: Prevents malicious or accidental writes to critical system directories.
  - Pro: Enhances security by enforcing strict boundaries for LLM operations.
  - Pro: Maintains data integrity within the project by ensuring files are written to expected locations.
  - Pro: Provides a clear audit trail and error message if an unauthorized write is attempted.
  - Con: Can be overly restrictive if not configured carefully for legitimate use cases.
  - Con: Requires careful definition and maintenance of allowed write paths.
- **README Documentation Alignment**: Establish a process to ensure the `README.md` accurately reflects the CLI's current capabilities and usage (vs manual updates, vs leaving it outdated).
  - Pro: Improves user experience by providing accurate and up-to-date instructions.
  - Pro: Reduces support burden by clarifying features and usage.
  - Pro: Enhances project professionalism and credibility.
  - Con: Requires dedicated effort to maintain, potentially integrating into CI/CD.
  - Con: Risk of drift if the update process isn't rigorously followed.

## API Contracts

- `tasks_json_path`: `Path` object pointing to the `TASKS.json` file.
- `FileNotFoundError`: If `tasks_json_path` does not exist.
- `json.JSONDecodeError`: If the file content is not valid JSON.
- `pydantic.ValidationError`: If any task definition in the JSON does not conform to the `TaskDefinition` schema.
- `IOError`: For other file system related issues.
- `base_project_path`: `Path` object representing the root directory of the current project.
- `proposed_target_path`: `Path` object representing the absolute file path suggested by the LLM for writing.
- `allowed_subdirectories`: `Optional[List[str]]` of subdirectory names (e.g., `['src', 'tests']`) that LLMs are explicitly permitted to write into. If `None`, writing is allowed anywhere within the `base_project_path`.
- `SecurityError`: A custom exception indicating the proposed path is outside `base_project_path` or not within `allowed_subdirectories`.
- `ValueError`: If `base_project_path` is not an absolute directory or other path-related issues.

## Success Criteria

- **Quality**: All `except Exception:` blocks in `ProjectAnalyzer` and `AutopilotOrchestrator` are replaced with specific exception handling.
- **Security**: LLM-initiated file write operations are strictly confined to the project root and explicitly allowed subdirectories, with 100% test coverage for path validation logic.
- **Reliability**: Task parsing no longer fails due to malformed LLM output; instead, it relies on `TASKS.json` schema validation, reducing parsing-related runtime errors by 90%.
- **Maintainability**: The `README.md` accurately describes all current CLI entry points, options, and the role of `TASKS.json`, as verified by a manual review and potentially a linting tool.
- **Observability**: Critical errors, especially those related to security violations or task definition parsing, are logged with appropriate severity levels and stack traces.

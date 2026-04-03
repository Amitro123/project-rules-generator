# Watch Mode Analysis: Issues & Potential Improvements

This document summarizes the technical findings from the investigation into the **`prg watch`** feature. While functional for basic use cases, the current implementation has several architectural limitations and potential bugs.

## Identified Issues

### 1. The "Missed Update" Race Condition 
The `_PRGHandler` uses a simple `_running` boolean to prevent overlapping analysis runs.
- **Problem**: If a file is saved while an analysis is already in progress, and the 2-second debounce timer fires *before* that analysis completes, the new trigger is simply **dropped**.
- **Impact**: The `.clinerules/` rules can get out of sync with the latest code changes during active development.
- **Recommendation**: Replace the `_running` boolean with a "dirty bit" system (`_needs_rerun`). If a change occurs during an active run, queue one final run to catch the latest state.

### 2. Lack of `.gitignore` Support
The watch mode recursively monitors the entire project directory but does **not** check for ignored paths.
- **Problem**: Changes to heavy build artifacts (e.g., `.mypy_cache`), temporary files, or logs in watched folders (like `tests/`) will trigger expensive re-analysis runs pointlessly.
- **Impact**: Unnecessary CPU usage and potentially slower performance in large projects.
- **Recommendation**: Integrate the `pathspec` library to filter out ignored paths in the `_should_trigger` logic.

### 3. Hardcoded Watch List Gaps
The `WATCH_FILES` set is currently missing several modern project configuration and dependency standards.
- **Missing Files**: `poetry.lock`, `Pipfile.lock`, `package-lock.json`, and `.gitignore` itself.
- **Impact**: Changes to these critical project files will not trigger a re-analysis of the coding rules.
- **Recommendation**: Expand `WATCH_FILES` to include all standard dependency lock files and top-level configuration markers.

### 4. Limited File Event Coverage
The current implementation only handles `on_modified` and `on_created` events.
- **Problem**: It misses `on_moved` and `on_deleted` events.
- **Impact**: Renaming a file (e.g., `README.txt` to `README.md`) may not trigger an update. Deleting a key project file also fails to trigger a cleanup or re-analysis.
- **Recommendation**: Add handlers for `on_moved` and `on_deleted` to the `_EventBridge` class.

## Summary of Findings

| Category | Severity | Description |
| :--- | :--- | :--- |
| **Race Condition** | High | Changes during active analysis are dropped. |
| **Efficiency** | Medium | Ignored files trigger redundant re-scans. |
| **Completeness** | Low | Modern lock files (`poetry`, `npm`) are ignored. |
| **Robustness** | Low | File renames and deletions aren't handled. |

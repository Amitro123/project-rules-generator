# Agent Context & Engineering Instructions

## 📌 Project Snapshot
- **Current Commit:** `9fd697d`
- **Overall Rating:** 7.4/10
- **Status:** Mid-hardening. Packaging/Typing are stable, but security-critical paths in `TaskImplementationAgent` require immediate attention.

---

## 🛡️ Critical Guardrails: Path Sanitization
The agent must treat all LLM-generated paths as untrusted/hostile. **Do not** rely on native `pathlib` for cross-platform validation.

### Implementation Requirements for `_sanitize_path()`:
1. **Normalization:** Replace all backslashes `\\` with forward slashes `/`.
2. **Drive/Root Blocking:** Reject paths starting with drive letters (e.g., `C:/`) or UNC/Network paths (e.g., `//server`).
3. **Traversal Prevention:** Explicitly reject leading slashes, empty segments, and `..` (parent directory) markers.
4. **Reconstruction:** Rebuild a safe relative POSIX path from allowed components only.

---

## 🚀 Immediate Implementation Tasks

### 1. Security Fix (High Priority)
- **Target:** `task_agent.py` -> `TaskImplementationAgent._sanitize_path()`
- **Goal:** Fix the 2 failing tests in `test_task_agent.py`.
- **Constraint:** Ensure the fix is OS-agnostic (the sanitizer should handle Windows paths correctly even when running on Linux).

### 2. Test Coverage Expansion
Add the following cases to `test_task_agent.py`:
- Mixed format: `C:/tmp/x.py`
- Network/UNC: `\\\\server\\share\\x.py`
- Malformed: `src//foo.py`, `path/with trailing space `

### 3. Modularization & Refactoring
Reduce complexity in "top-heavy" orchestration modules:
- `generator/analyzers/readme_parser.py`
- `generator/rules_generator.py`
- `cli/analyze_pipeline.py`

---

## 📐 Architecture & Standards
- **Typing:** Maintain 100% Green MyPy status.
- **Packaging:** Keep `pyproject.toml` dependencies strictly separated (core vs. optional provider extras).
- **Strategy:** Move from "Full-file Overwrite" to "Patch/Diff" application for better stability in large projects.

---

## 📝 Performance Scorecard
| Area | Current Score | Target |
| :--- | :--- | :--- |
| **Security** | 6.2 | 9.0 |
| **Runtime Reliability** | 6.8 | 8.5 |
| **Maintainability** | 6.8 | 8.0 |
| **Overall** | **7.4** | **8.5+** |

> **Note:** Do not cut a stable release until the path sanitizer is bulletproof.
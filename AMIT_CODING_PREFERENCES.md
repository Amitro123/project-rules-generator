# AMIT CODING PREFERENCES v1.0
Session: 2026-02-05 - Generating Rules
Learned:

## ❌ Rejected
- None yet.

## ✅ Approved
- **Structure**: Follow `project-rules-generator-rules.md` conventions.
- **Tech Stack**: Python (CLI), No React (this is a CLI tool).
- **Testing**: pytest coverage required. Update tests when templates change.
- **Docs**: README must be kept in sync.
- **Generator**: Dynamic fallbacks are good, but specific templates take precedence.
- **Robust Imports**: When using optional dependencies like `tqdm`, ensure fallbacks implement the full interface (e.g., context manager protocol) to avoid crash in CI/minimal environments.
- **Cleanup**: Always ensure `__pycache__` is ignored and deleted. Use `clean.ps1` helper.
- **Priority Logic**: When designing override systems, use a clear, configurable list (e.g., `preference_order`) and deterministic numeric priorities (inverted index) to avoid ambiguity.
- **Documentation**: Visual diagrams (ASCII) are highly valued for explaining complex flows like orchestration.
- **Refactoring Safety**: When removing features, immediately remove associated tests to prevent ghost failures.
- **Testing Mocks**: Verify mock targets against actual function signatures to avoid AttributeErrors.
- **Instantiation**: In factory functions (like `setup_orchestrator`), ensure objects are assigned to variables before use.

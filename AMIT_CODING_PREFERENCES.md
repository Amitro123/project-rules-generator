# AMIT CODING PREFERENCES v1.1
Session: 2026-02-11 - Quality Feedback Loop Implementation
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
- **Src Layout**: When using `src/` layout, ALWAYS include `"src"` in `pyproject.toml` `packages` AND ensure `src/__init__.py` exists. Add `sys.path` injection in entry points for robustness.
- **Encoding Safety**: When handling AI responses, ALWAYS explicitly clean encoding artifacts (e.g., `.encode('utf-8', errors='replace').decode('utf-8')`) and strip common corruptions like `ג€"` (em dash artifact) before processing.
- **Iterative Improvement**: When implementing feedback loops, always include: (1) early exit on target reached, (2) max_iterations safety limit, (3) best attempt tracking, (4) comprehensive error handling.
- **Test Security**: When testing file operations with ContentAnalyzer, pass `allowed_base_path=tmp_path` to avoid security check failures in tests.
- **CLI Flags**: When adding new CLI options, update both the decorator AND the function signature to avoid parameter mismatch errors.
- **Quality Thresholds**: Raise quality bars progressively (85 → 90) to ensure continuous improvement without breaking existing workflows.
- **Workflow Stability**: Don't over-engineer. Use simple, proven patterns (e.g., Global Cache + Symlinks) instead of complex new abstractions unless necessary.
- **Naming Conventions**: Stick to functional names (e.g., `pytest-testing-workflow`) over abstract ones (e.g., `tech-patterns`) to maintain clarity and reusability.
- **Config Single Source of Truth**: NEVER allow duplicate configuration files (e.g., `.clinerules/clinerules.yaml` vs `.clinerules.yaml`). Always enforce a single root source of truth to avoid cache confusion.

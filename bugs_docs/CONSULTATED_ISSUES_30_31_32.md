# GitHub Issues: 30, 31, 32 Consolidated

This document contains a consolidated view of GitHub issues #30, #31, and #32 for the Project Rules Generator (PRG).

---

## Issue #30: Config/schema drift: OpenAI is advertised and routed, but LLMConfig.provider still rejects it

### Summary
There is still a provider-support mismatch across the repo. On current main (1433e933):
- `README.md` advertises OpenAI support
- `generator/ai/ai_strategy_router.py` supports openai
- `cli/utils.py` auto-detects `OPENAI_API_KEY`
- **But** `prg_utils/config_schema.py` still restricts providers to `["anthropic", "gemini", "groq"]`.

The schema layer rejects `openai` even though higher layers expose it as a first-class provider.

### Why this matters
This creates a contract mismatch between docs, runtime behavior, and config validation. Users can reasonably assume OpenAI is fully supported, but config-driven flows may fail validation.

### Suggested fix
Update the schema so all user-facing layers agree on the same provider set.
- Add "openai" to `LLMConfig.provider`.
- Audit defaults/model names for consistency.
- Add a schema validation test for OpenAI.
- Add an integration test for OpenAI-configured paths.

---

## Issue #31: Regression: --auto-generate-skills can crash with SameFileError when reusing learned skills

### Summary
On current main (1433e933), the CLI can fail during `--auto-generate-skills` when a learned skill is classified as `reuse` and the resolved source path and destination path refer to the same file.

### Repro
Test failure: `tests/test_enhanced_integration.py::TestCLIIntegration::test_auto_generate_skills_flag`

Traceback excerpt:
```
shutil.SameFileError: PosixPath('/home/user/.project-rules-generator/learned/click-cli.md') and PosixPath('/tmp/.../test-project/.clinerules/skills/learned/click-cli.md') are the same file
```

Triggered from: `generator/skill_generator.py` in the `action == "reuse"` branch during `shutil.copy2(resolved, dest)`.

### Why this matters
This breaks a user-visible CLI path (`prg analyze ... --auto-generate-skills`) even though the project otherwise largely passes tests.

### Suggested fix
Before copying in the reuse branch, guard for equivalent source/destination paths:
- Compare `resolved.resolve()` and `dest.resolve()`.
- Skip the copy when they are the same file.
- Add a regression test covering the reuse path with project-linked learned skills.

---

## Issue #32: Main branch quality gate drift: tests still fail on HEAD and lint/type checks are not clean

### Summary
A second-pass review on current main (1433e933) still finds quality-gate drift on HEAD.

### Local Results
- `pytest -q` → 1 failed, 529 passed, 11 skipped
- `ruff check .` → 37 issues
- `mypy generator cli prg_utils main.py` → 5 errors

### Notable Examples
- Failing integration test: `tests/test_enhanced_integration.py::TestCLIIntegration::test_auto_generate_skills_flag` (Issue #31)
- Multiple `E402` / import-order violations in `cli/cli.py`, `generator/skill_generator.py`, etc.
- Type issues including provider client imports and a `tech_detector.py` attribute error report.

### Why this matters
Having main not fully clean makes it harder to trust badges, releases, and follow-up regressions.

### Suggested fix
1. Fix the currently failing integration test (#31).
2. Make `ruff check .` pass on main.
3. Tighten code to pass current mypy checks or scope mypy config so the signal is actionable.
4. Update badges/release claims only after cleanup.

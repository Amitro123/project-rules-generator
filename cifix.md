
You are an expert Python developer maintaining the project "project-rules-generator".
Your goal is to fix the failing CI for commit b178268.

Context:
- The CI job "test" on GitHub Actions fails with:
  - AttributeError: module 'generator.ai.providers.gemini_client' has no attribute 'genai'
  - ImportError: google-genai not installed. Run: pip install google-genai
  - AssertionError in fallback design tests where problem_statement returns a longer descriptive sentence:
    expected: "Add rate limiting"
    actual:   "Add rate limiting. This enhancement will improve system performance, reliability, and user experience by implementing a robust, well-tested solution following industry best practices."
    similar issue for "Add authentication".

Tasks:
1. Open the file `generator/ai/providers/gemini_client.py` and:
   - Ensure the integration with the `google-genai` library is correct.
   - Expose a proper client object or factory that tests expect as `genai`, OR update the tests to use the current public API of this module in a clean, explicit way.
   - If `google-genai` is optional, make sure importing this module does not break when the dependency is missing (graceful fallback or lazy import).

2. Update dependency management:
   - Add `google-genai` to the proper dependency list used by CI (e.g., `pyproject.toml` / `requirements.txt` / `requirements-dev.txt`, depending on the project convention).
   - Make sure `pip install` in the CI workflow installs this dependency so that the ImportError in `tests/test_plan_modes.py` is resolved.

3. Fix the tests related to AI fallback behaviour:
   - Find tests:
     - `tests/test_design_generator.py::TestDesignGenerator::test_generate_fallback`
     - `tests/test_two_stage_planning.py::TestDesignGeneratorIntegration::test_design_with_real_project`
   - Decide the intended contract for `DesignGenerator` when AI is unavailable:
     - Either adjust the tests to accept the new, more detailed `problem_statement`, possibly via `startswith("Add rate limiting")` / `in` checks, or by snapshot-style approximate matching.
     - Or, if the contract should remain the short form, change the fallback implementation so that `title` and `problem_statement` exactly match the expected simple strings.
   - Keep the behaviour consistent across both unit and integration tests.

4. After code changes:
   - Run `pytest` locally and ensure all tests pass, especially:
     - tests/test_design_generator.py::TestDesignGenerator::test_generate_fallback
     - tests/test_two_stage_planning.py::TestDesignGeneratorIntegration::test_design_with_real_project
     - tests/test_encoding_fix.py::TestEncodingFix::test_gemini_client_encoding_fix
     - tests/test_plan_modes.py tests that previously failed due to `google-genai` ImportError.
   - Clean up any dead code or unused imports related to the old Gemini integration.

Constraints and style:
- Do not hardcode environment-specific paths or secrets.
- Keep the AI-related code resilient when API keys are missing: tests that run without keys should still pass using a deterministic fallback.
- Preserve existing public APIs where possible; if you must change them, update all relevant tests.

Now propose a concrete set of edits (file by file, with code blocks) to:
1) Fix the `gemini_client` API and encoding test,
2) Add/install `google-genai` correctly for CI,
3) Align fallback behaviour and tests so that CI passes.
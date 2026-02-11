You are an expert refactoring and merge-fix agent working on
`Amitro123/project-rules-generator` for PR "Feat/jules features v2" (PR #8).

Scope:
Apply the latest Coderabbit review comments from 10:52 (outside-diff comments),
with priority: Critical issues first, then Major, then Minor.

Rules:
- Work in the repo root.
- Do not change public behavior beyond what is required to fix bugs or
  resolve merge conflicts.
- Prefer targeted, minimal edits and keep commits logically grouped.
- After changes, ensure the project still installs and tests run.

Critical tasks (fix these first):

1) Resolve merge conflicts in rules/skills/config files
   - `.clinerules/skills/learned/error-handling.md`:
     - Remove all Git conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
     - Keep ONLY the error-handling skill content (lines 2–29).
     - Delete the pydantic-model-validation block and its markers.
   - `.clinerules/clinerules.yaml`:
     - Resolve both conflict regions (around lines 20–24 and 33–46).
     - Remove all conflict markers so the YAML parses cleanly.
     - Keep the intended entries (e.g., keep `readme-improver.md` instead of `SKILL.md`,
       include all new learned skills, and fix any counts).
   - `PLAN.md`:
     - Remove all conflict markers and choose the intended final plan text
       for each conflict region.
   - `.clinerules/rules.md`:
     - Resolve all four conflict regions:
       * DEPENDENCIES (11 vs 10 packages),
       * TESTING (34/240 vs 31/218),
       * PRIORITIES wording,
       * Anti-Patterns wording.
     - Remove `<<<<<<< HEAD` / `=======` / `>>>>>>> main`.
     - Produce one coherent, finalized version of each section.

2) Click CLI / provider wiring bugs in main.py
   - In `design()`:
     - Add `provider` to the function signature so it matches the Click
       `--provider` option.
     - Fix env var setting so that:
       - When `provider == "gemini"` and `api_key` is provided, set
         `os.environ["GEMINI_API_KEY"] = api_key`.
       - When `provider == "groq"` and `api_key` is provided, set
         `os.environ["GROQ_API_KEY"] = api_key`.
   - In the `plan` command:
     - After detecting the provider, do NOT always set `GEMINI_API_KEY`.
     - Instead:
       - If `provider == "gemini"` and `api_key` is provided, set
         `GEMINI_API_KEY`.
       - If `provider == "groq"` and `api_key` is provided, set
         `GROQ_API_KEY`.

3) Gemini dependency for ContentAnalyzer / GeminiClient
   - Ensure the `google-genai` package is a first-class dependency:
     - Add `google-genai>=0.2.0` to:
       - `requirements.txt`,
       - `pyproject.toml` (main dependencies),
       - `setup.py` (`install_requires` list),
       - and `requirements-dev.txt` so CI can run `tests/test_encoding_fix.py`.
   - Confirm that importing and instantiating `GeminiClient` (via
     `create_ai_client(provider="gemini")`) works without ImportError.

Major tasks:

4) ContentAnalyzer patch prompt & markdown fences
   - In `generator/content_analyzer.py`:
     - In `_generate_patch`, do NOT embed the full `content` into the prompt.
       Instead:
       - Introduce `truncated_content = content[:self.config.max_content_length]`
         (or an equivalent patch-specific limit).
       - Use `truncated_content` in the prompt under "Current Content".
     - Improve markdown fence stripping for `improved`:
       - Replace the two `re.sub` calls so they:
         - Strip an opening fence with optional language:
           pattern equivalent to `^```(?:\w+)?\n`
           (handles both ``` and ```markdown).
           (Do not literally escape backticks here, keep the regex semantics.)
         - Strip a closing fence allowing trailing whitespace/newlines:
           pattern equivalent to `\n```\s*$`.

5) Planning regex and progress printing
   - In `generator/planning/project_planner.py`:
     - Update `phase_pattern` so only `##` headers (not `###`) start a new phase:
       - Use a lookahead that rejects an extra `#`, e.g.:
         `r'##\s+(.+?)\n(.*?)(?=\n##(?!#)|\Z)'`.
   - In `generator/planning/plan_parser.py`:
     - In the `lines = [...]` list that prints progress:
       - Replace the two empty `f""` literals with plain `""` strings to
         satisfy Ruff (F541).

6) Readme generator wiring
   - In `generator/readme_generator.py`:
     - Wherever `generate_readme_with_llm` is called interactively,
       update the call site to pass through any `provider` and `api_key`
       arguments once they are wired into the function.
     - In `generate_readme_with_llm` itself, forward `provider` and `api_key`
       into `LLMSkillGenerator(...)`, e.g.:
       `generator = LLMSkillGenerator(provider=provider, api_key=api_key)`.

Minor tasks (as time allows):

7) Tests and mocks
   - In `tests/conftest.py`:
     - Update the mock `generate()` method for the AI client to include
       a `temperature` parameter with default (e.g. `temperature=0.7`) so
       its signature matches the real client.
   - In `tests/test_content_analyzer.py`:
     - For `test_patch_generation_for_low_score`:
       - Remove the `if report.score < 85:` guard.
       - Assert explicitly that `report.score < 85` and then that
         `report.patch is not None` (or document a fallback if AI is unavailable).

8) Main quality-check block and flags
   - In `main.py` quality check block:
     - Replace `from src.ai.content_analyzer import ContentAnalyzer` with
       the proper package import (e.g. `from generator.ai.content_analyzer import ContentAnalyzer`).
     - Remove `f` prefixes from strings that have no placeholders.
     - Replace `[fp for fp, _ in reports if _.score < 85]` with
       `[fp for fp, report in reports if report.score < 85]`.
     - Narrow the exception handling around `commit_files` to a more
       specific exception, and log or echo a clear error.
   - For `--ide` and `--scan_all` in `analyze`:
     - Either:
       - Wire `ide` into `IDERegistry.register(ide)` after generating `.clinerules`,
         and pass `scan_all` into the scan logic,
       - Or remove these options and parameters if they are truly unused.

9) Path validation for interactive editor
   - In `main.py` interactive mode (plan subtasks):
     - Before calling `subprocess.Popen([editor, str(full_path)])` or
       creating files, resolve `full_path` and ensure it is within
       `project_path` (no path traversal, symlink escape, etc.).
     - If a path is outside the allowed tree, skip it and print a warning
       instead of opening it.

Execution:
1. Implement all Critical items (conflicts, CLI/provider bugs, dependencies).
2. Implement Major items (ContentAnalyzer truncation, markdown fence fix,
   planning regex, readme wiring).
3. Apply Minor cleanups (tests, mocks, quality-check imports, path validation).
4. Run the test suite (pytest) and ensure it passes.
5. Output unified diffs and a short explanation (1–2 sentences) per file modified.

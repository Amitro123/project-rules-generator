# Pre-Open-Source Audit — Skills & Rules Mechanisms

**Audit date:** 2026-04-22
**Auditor:** Opus agent, read-only walk of repo as a first-time visitor
**Scope:** Only the skills + rules mechanisms, not the whole codebase
**Context:** Batches A/B/C/D already shipped. End-to-end AI flow scores 100/100; tests 1367 green; ruff/black/isort clean.

**Recommendation:** Fix items 1–10 and the project can be published without cringing. Item 1 is a hard stop — without it, `pip install project-rules-generator` produces a broken install.

---

## 🔴 BLOCKERS — fix before publishing

### [x] 1. Package-data path is wrong (will break `pip install`) ✅ FIXED 2026-04-22

`pyproject.toml` declares:
```toml
[tool.setuptools.package-data]
generator = ["skills/**/*", "templates/**/*"]
```
But the actual Jinja templates live at **repo-root** `templates/` — outside the `generator/` package. After `pip install`, any loader that does `Path(__file__).parent.parent / "templates" / "SKILL.md.jinja2"` will 404.

**Evidence:** `ls generator/templates` → not found; `ls templates/` → `SKILL.md.jinja2`, `RULES.md.jinja2`, `skills/`, `rules_template.yaml`.

**Fix options:**
- Move `templates/` under `generator/templates/` and update loader paths, OR
- Switch to `importlib.resources` with files pointed at the installed location, OR
- Add a `MANIFEST.in` entry that pulls the external directory into the sdist (still needs loader fix).

**Verification:** `pip wheel . && unzip -l project_rules_generator-*.whl | grep -E "(templates|SKILL\.md\.jinja2)"` must show the template files inside the wheel.

### [x] 2. `.clinerules/clinerules.yaml` references skills that don't exist ✅ FIXED 2026-04-22

Lists `skills/learned/api-client-patterns.md`, `branch-management.md`, `diff-patterns.md`, `coverage-patterns.md` — none are on disk. Any agent consuming the manifest will 404 on every reference.

**Fix:** Regenerate `clinerules.yaml` from current disk state, or delete it and let `prg` re-emit on first run.

### [x] 3. `temp_test_project-workflow.md` is committed ✅ FIXED 2026-04-22

Literal scratch file with placeholder `TEMP_TEST_PROJECT` text. Path: `.clinerules/skills/learned/temp_test_project-workflow.md`. Currently tracked.

**Fix:** `git rm`; add `temp_*` / `scratch*` globs to the generator's skill-name refusal list.

### [x] 4. Placeholder text shipped as skill content ✅ FIXED 2026-04-22

`gemini-api.md`, `groq-api.md`, `pydantic-validation.md`, `gitpython-ops.md` all contain literal `[One sentence: what this skill does…]`, `[list false-positive phrases]`, `[placeholder]`. These are visitors' first impression of the tool's output.

**Fix:** Delete or regenerate. Add a placeholder-leak detector check before writing to `learned/` (the detector function already exists — `generator/ai/hardening.py::contains_unfilled_placeholders`).

### [x] 5. Developer scratch docs tracked in repo ✅ FIXED 2026-04-22

`CR.md`, `leftovers.md`, `GITHUB_ISSUES_REVIEW.md`, `TASKS.json`, `capture_terminal.py`, `capture_ralph_terminal.py`, `_bmad/`, `bugs_docs/`, `dist/project_rules_generator-0.3.0-py3-none-any.whl`, `build/` tree.

**Fix:** `git rm` these; extend `.gitignore` to prevent recurrence.

---

## 🟠 EMBARRASSING — visitors will mock on Twitter

### [x] 6. Duplicate/conflicting learned skills with different shapes ✅ FIXED 2026-04-22

Side-by-side in `.clinerules/skills/learned/`:
- `deadcode/SKILL.md` (empty description) vs `dead-code/SKILL.md` (proper) — pick one naming.
- `gitpython/` (only `diff-patterns.yaml`, no SKILL.md) vs `gitpython-ops/SKILL.md` vs loose `gitpython-ops.md` — three shapes for the same concept.
- `fastapi-api/SKILL.md` (uses `allowed-tools:` + `triggers:`) vs loose `fastapi-api-workflow.md` (uses `tools:` + `auto_triggers:`; description is literally `# Requires GEMINI_API_KEY`).
- `pytest-testing/`, `pytest-patterns/`, `pytest-best-practices/`, `pytest/`, `pytest-testing-workflow.md` — **five** pytest skills.

**Fix:** Declare directory-shape (`<slug>/SKILL.md`) canonical; delete loose `*.md` twins; dedupe pytest/gitpython/deadcode down to one each.

### [x] 7. Empty descriptions in shipped skills ✅ FIXED 2026-04-22

`cleanup/SKILL.md` → `" workflow for this project"` (leading space).
`deadcode/SKILL.md` → same.
`fastapi-api-workflow.md` → description is literally `# Requires GEMINI_API_KEY`.

**Fix:** Regenerator should reject empty/prefix-only descriptions.

### [x] 8. Inconsistent frontmatter surface ✅ FIXED 2026-04-22

Scorer accepts three trigger shapes (`triggers: [list]`, `auto_triggers: {keywords: [...], project_signals: [...]}`, list-of-dicts) and two tool keys (`tools:` / `allowed-tools:`). Current `.clinerules/` examples use **all** variants simultaneously. A new contributor has no idea what to write.

**Fix:** Pick one canonical shape in docs + `CONTRIBUTING.md`; deprecate others with a warning; keep parse-tolerance.

### [x] 9. Shipped `.clinerules/rules.md` is stale ✅ FIXED 2026-04-22

`version: 2.0, generated: auto` with a toy tech list (`claude, gemini, gpt, groq, click, pydantic, gitpython`) — not representative of today's quality.

**Fix:** Either regenerate against the real repo or remove from git.

### [x] 10. No `.env.example` documenting API-key env vars ✅ FIXED 2026-04-22

`config.yaml.example` exists but there's no `.env.example` for `GEMINI_API_KEY` / `GROQ_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` (all read by `llm_skill_generator.py`).

**Fix:** Add `.env.example` listing all supported keys with comments about when each is used.

---

## 🟡 NICE-TO-HAVE — improves first impression, not blocking

### [x] 11. Missing `generator/py.typed` marker ✅ FIXED 2026-04-22

Code is fully type-hinted and mypy-configured, but without `py.typed` downstream users can't benefit from types.

**Fix:** Add empty `generator/py.typed`; list in package-data.

### [x] 12. No mention of `clean.ps1` in README Quick Start ✅ FIXED 2026-04-22

The repo ships a `clean.ps1` to purge `__pycache__` but the README doesn't reference it.

**Fix:** Add a "Housekeeping" line in the Quick Start section.

### [x] 13. CHANGELOG stops at v0.3.0 (2026-04-03) ✅ FIXED 2026-04-22

No entry for Batches A/B/C/D (atomic writes, concurrency-safe tracker, detector consolidation, placeholder detection, scorer crash fix, generator template fixes).

**Fix:** Add `[Unreleased]` section summarising these before cutting the public tag.

### [x] 14. No CONTRIBUTING skill-authoring guide ✅ FIXED 2026-04-22

`CONTRIBUTING.md` exists but doesn't explain:
- canonical skill shape,
- what `project_signals` mean,
- directory-vs-file layout choice,
- how to add a tech profile.

**Fix:** Add `docs/AUTHORING-SKILLS.md` and link from CONTRIBUTING.

### [x] 15. Decide what `.clinerules/` is for ✅ FIXED 2026-04-23 — chose **option (b)**

Currently neither a clear showcase (too messy) nor self-dogfooding-only.

**Fix — pick one:**
- (a) Gitignore it entirely; add a curated `examples/showcase-clinerules/` set, OR
- (b) **Keep it but regenerate cleanly post-Batch-D and label as "generated output, do not edit."** ← chosen

**Decision (2026-04-23):** option (b). The repo ships `.clinerules/` as
**self-dogfooding** — it's the output PRG produces when run against its own
source tree, kept in-tree so first-time visitors can inspect realistic
rules + skills without installing the tool first. `.clinerules/README.md`
labels the directory as "generated output, do not edit" and points readers
at the real generators. Transient artifacts (`rules.md`, `clinerules.yaml`,
`auto-triggers.json`) stay gitignored — only the curated skill corpus is
tracked. Regeneration will produce occasional diffs; those are expected
and not reviewed line-by-line.

### [x] 16. Security review — clean ✅

- All `subprocess.run` invocations in `generator/` use list-form args, **no `shell=True`** anywhere.
- `ContentAnalyzer.allowed_base_path` correctly `resolve()`s and uses `relative_to()` for traversal check.
- **No hardcoded `C:\Users\Dana` paths** in shipped Python.
- **No secrets, tokens, credentials committed.**
- `LLMSkillGenerator` prompts include project tree/README snippets but no secrets or absolute local paths beyond what the user explicitly analyses.

No action needed.

### [ ] 17. Over-broad `except Exception` in `ralph/engine.py:435`

Annotated with `# noqa: BLE001` justification. Acceptable — keep the comment-discipline convention elsewhere; no action needed unless more show up.

### [x] 18. Unicode emoji in logger output ✅ FIXED 2026-04-23

`✅ ❌ 💾 📝 ✏️` in `ralph/engine.py`. Crashes on Windows consoles without UTF-8 default.

**Fix:** Either force `sys.stdout.reconfigure(encoding='utf-8')` on CLI entry, or swap to ASCII markers (`[OK]`, `[FAIL]`, etc.).

### [x] 19. `.clinerules/skills/builtin/` in half-deleted state ✅ FIXED 2026-04-23

Current `git status`: `D .clinerules/skills/builtin/SKILL.md`, `D agent-architecture-analyzer.md`, etc., plus new `ci-lint-failures/`. State is inconsistent mid-commit.

**Fix:** Finish the deletion + regeneration before tagging a release.

---

## Recommended Fix Order

1. **#1** — package-data path (hard blocker; verify with `pip wheel`)
2. **#3, #4, #5** — pure `git rm` hygiene
3. **#2** — regenerate or delete `clinerules.yaml`
4. **#6, #7, #8** — dedupe and canonicalise the skill corpus
5. **#9, #19** — regenerate or remove shipped `.clinerules/`
6. **#10, #13** — `.env.example` + CHANGELOG (five-minute wins)
7. **#11, #12, #14, #18** — polish

Items 15, 17 are decisions / no-action-required.

---

## Progress Log

_(Updated as fixes land.)_

| Date | Batch | Item | Status | Commit |
|---|---|---|---|---|
| 2026-04-22 | OSS-1 | #1 package-data path | ✅ moved `templates/` → `generator/templates/`; fixed loaders; 1367 tests green; `pip wheel` ships all template files | (pending) |
| 2026-04-22 | OSS-1 | #3 temp_test_project leak | ✅ `git rm` the file; added `temp\|tmp\|scratch\|placeholder\|draft` prefix refusal to `SkillGenerator.create_skill`; 14 new tests | (pending) |
| 2026-04-22 | OSS-1 | #4 placeholder-leaked skills | ✅ deleted untracked `gemini-api.md`, `groq-api.md`, `pydantic-validation.md`, `gitpython-ops.md` from working tree | (pending) |
| 2026-04-22 | OSS-1 | #5 scratch docs | ✅ `git rm CR.md leftovers.md`; extended `.gitignore` with scratch patterns | (pending) |
| 2026-04-22 | OSS-1 | #2 stale clinerules.yaml | ✅ `git rm .clinerules/clinerules.yaml` (generated output, regenerated by `prg analyze`); added to `.gitignore` | (pending) |
| 2026-04-22 | OSS-2 | #6 duplicate skills | ✅ `git rm -r` duplicate dirs: `fastapi-api/`, `gitpython/`, `pytest/`, `pytest-patterns/`, `python-cli/`; canonical shape is `<slug>/SKILL.md` | (pending) |
| 2026-04-22 | OSS-2 | #7 empty descriptions | ✅ fixed `qa-and-bugs-finder` and `test-refactor` descriptions; added `description < 40 chars` + whitespace-leak checks to `validate_quality()` | (pending) |
| 2026-04-22 | OSS-2 | #8 frontmatter shape | ✅ documented canonical shape (directory form, `description: \|` block scalar, `allowed-tools` as list, triggers in description) in `CONTRIBUTING.md` | (pending) |
| 2026-04-22 | OSS-2 | #9 stale rules.md | ✅ `git rm .clinerules/rules.md` + added to `.gitignore` (generated by `prg create-rules`) | (pending) |
| 2026-04-22 | OSS-3 | #10 .env.example | ✅ expanded to cover `GOOGLE_API_KEY`, `OPIK_API_KEY`, and optional model overrides (`GEMINI_MODEL`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`) | (pending) |
| 2026-04-22 | OSS-3 | #11 py.typed | ✅ added `generator/py.typed` + listed in `[tool.setuptools.package-data]` so PEP 561 consumers see inline type hints | (pending) |
| 2026-04-22 | OSS-3 | #12 README clean.ps1 | ✅ added Housekeeping block to Quick Start with Windows (`pwsh clean.ps1`) + Unix (`find … -exec rm`) commands | (pending) |
| 2026-04-22 | OSS-3 | #13 CHANGELOG | ✅ added `[Unreleased]` section summarising Batches A–D and audit items #1–#14 | (pending) |
| 2026-04-22 | OSS-3 | #14 authoring guide | ✅ added `docs/AUTHORING-SKILLS.md` (canonical shape, frontmatter, required body, signals, tech profiles, worked examples, common mistakes); linked from `CONTRIBUTING.md` | (pending) |
| 2026-04-23 | OSS-4 | #15 .clinerules showcase | ✅ added `.clinerules/README.md` labelling the dir as generated output with a "do not edit" notice and an editor-map table pointing readers at the real generators | (pending) |
| 2026-04-23 | OSS-4 | #18 emoji crash | ✅ extracted Windows UTF-8 reconfigure into shared `prg_utils.logger.ensure_utf8_streams()`; called from `cli/cli.py` and `generator/ralph/engine.py` module-top so library consumers no longer crash on `🚀`/`✅` | (pending) |
| 2026-04-23 | OSS-4 | #19 builtin half-deleted | ✅ verified working tree clean; all `skills/builtin/` dirs present in canonical `<slug>/SKILL.md` shape | (pending) |
| 2026-04-23 | CR-1 | CR blocker: missing `packaging` | ✅ added `packaging>=23.0` to `[project].dependencies` (was only in `requirements.txt`); fresh wheel installs no longer crash in `dependency_parser` | (pending) |
| 2026-04-23 | CR-1 | CR: pathspec conflict | ✅ verified `pathspec>=0.11.0` (no upper bound) in both `pyproject.toml` and `requirements.txt`; black 26.3.0 resolves cleanly against it | (pending) |
| 2026-04-23 | CR-2 | CR: allowed-tools string shape | ✅ converted `allowed-tools: "Bash Read Write Edit Glob Grep"` to YAML list form in `api-integration/*.yaml` — last two sites carrying the legacy string | (pending) |
| 2026-04-23 | CR-2 | CR: stale "≥437 passed" | ✅ manual-qa skill now expects "all pass, no regression vs captured baseline" instead of a raw threshold that silently rots as the suite grows | (pending) |
| 2026-04-23 | CR-3 | CR: stub `type-checking` skill | ✅ rewrote description (4 concrete trigger lines) + Purpose (pain-oriented); stripped absolute `C:\Users\Dana\…\project-rules-generator` path from the generated Project Context block | (pending) |
| 2026-04-23 | CR-3 | CR: duplicate readme skills | ✅ `git rm -r .clinerules/skills/project/readme-improver/`; kept the project-scoped `readme-improvement/` variant with real triggers | (pending) |
| 2026-04-23 | CR-3 | CR: unused type-ignore in skill_tracker | ✅ changed both platform-conditional `msvcrt`/`fcntl` imports to `# type: ignore[import-not-found,unused-ignore]` so mypy passes on both Windows and Linux (mypy: "no issues found") | (pending) |
| 2026-04-23 | CR-3 | CR: doc confusion `generator/templates/skills/` vs `generator/skills/builtin/` | ✅ split the skill-layer table in `CONTRIBUTING.md` and `docs/AUTHORING-SKILLS.md` into **source path / runtime path / created by** columns; added a blockquote footnote clarifying that `generator/templates/skills/` holds YAML scaffolds (consumed by `BuiltinSkillsSource`), not finished skills — new builtin skills go to `generator/skills/builtin/<name>/SKILL.md` | (pending) |
| 2026-04-23 | CR-2 | CR: CI smoke depth | ✅ verified `ci.yml` smoke-test job installs the wheel and runs `prg init` + `prg analyze` on a temp project — catches import-level regressions like the missing `packaging` dep | (pending) |

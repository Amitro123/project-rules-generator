# Known Issues

This page tracks known quality issues in PRG's LLM-dependent commands
(`prg design`, `prg plan`, `prg review`, `prg ralph`) and the architectural
limitations the maintainers have acknowledged but not yet closed.

Offline commands (`prg init`, `prg analyze`, `prg watch`, `prg create-rules`)
are not covered here — they do not depend on an LLM and are not subject to
the classes of failures listed below.

---

## `prg design` / `prg plan` quality issues

Originally surfaced by running `prg design` and `prg plan --from-design` on
real projects. All four issues below have been **hardened** — they no longer
fail silently, retry on invalid output, and ground themselves against the
real project tree. LLM-driven output is still probabilistic, so edge cases
remain possible; if you see one, please [open an issue](https://github.com/Amitro123/project-rules-generator/issues).

### Issue 1 — `prg design`: empty Success Criteria bullets

**Symptom (before fix):**
```markdown
## Success Criteria

- **Code Modularity**:
- **Testability**:
```
Labels with empty bodies — useless for planning.

**Root causes:**
1. `_extract_bullets()` only captured the first line of each bullet.
2. When the LLM truncated mid-document (Groq Llama 3.1 8B output cap), the
   whole response failed to parse and the fallback returned a minimal stub
   with no criteria at all.

**Hardening (current behaviour):**
- Multi-line `_extract_bullets()` accumulates continuation lines.
- `_call_llm()` uses `max_tokens=4000` (safe under the Groq output cap) and
  retries once with a repair hint when the response lacks `Success Criteria`
  or `Architecture Decisions` sections (`generator/ai/hardening.py`).
- When `Design.from_markdown()` still fails, `_salvage_partial_design()`
  extracts whatever sections are parseable (title, problem, criteria,
  contracts, models) rather than discarding the whole response.

**Status:** Hardened. Regression-tested in `tests/test_llm_hardening.py`.

---

### Issue 2 — `prg plan --from-design`: under-decomposition

**Symptom (before fix):** one paraphrased task returned instead of ~5 per design.

**Root cause:** the fallback to the structural `_tasks_from_design()`
builder only fired when the LLM returned exactly one task whose title
string-equalled `design.title[:80]`. A paraphrased title (the typical
LLM behaviour) bypassed the fallback.

**Hardening:**
- Fallback trigger widened to **`len(tasks) < 3`** regardless of title.
- `decompose()` and `from_design()` call the LLM with a validator that
  requires at least three `### N.` task headings, retrying once when the
  validator rejects the output.
- `max_tokens` raised to `8000` so multi-task bodies are no longer cut
  off mid-stream.

**Status:** Hardened. Tested with a paraphrased-title response in
`tests/test_llm_hardening.py::TestFromDesignFallback`.

---

### Issue 3 — `prg plan`: hallucinated file paths (`src/` in a non-`src/` project)

**Symptom (before fix):**
```markdown
**Files:**
- `src/config.py` (new)
```
Written to a project that actually organises code under `generator/`.

**Root causes:**
1. `_build_prompt()` (the plain `decompose` path) never injected the real
   project tree — only `from_design` did.
2. The prompt's example text literally said `e.g. \`src/api.py\``, which acts
   as a strong few-shot anchor for the LLM.
3. The task agent's system prompt also showed `[FILE: src/main.py]` as an
   example.

**Hardening:**
- `_build_prompt()` now calls `build_project_tree(project_path)` and injects
  it under a `## Project Structure (use THESE directories in Files fields)`
  heading.
- The prompt example path is chosen from the project's real top-level source
  directories (`discover_source_dirs`). If no source dir is discoverable,
  the placeholder `<package>/api.py` is used instead of `src/`.
- `TaskImplementationAgent._build_prompt` injects the project tree when
  `project_context["project_path"]` is set; the system prompt uses `<pkg>`
  rather than `src/`.
- **Post-hoc grounding:** `_ground_task_paths()` rewrites any remaining
  top-level paths that don't exist in the project tree (e.g. `src/api.py` →
  `generator/api.py`). Paths that already reference real directories, and
  bare filenames like `README.md`, are left unchanged. Paths that cannot
  be grounded are kept verbatim — they surface the bug rather than hide it.

**Status:** Hardened. Tested in
`tests/test_llm_hardening.py::TestPathGrounding` and `TestDiscoverSourceDirs`.

---

### Issue 4 — `prg plan`: task content truncated mid-sentence

**Symptom (before fix):**
```markdown
- Define a Pydantic `BaseModel` named `LLMConfig` with fields: `provider: str`, `model: str`, `api_key:
```

**Root causes:**
1. `max_tokens=5000` was not always enough for 5–8 detailed subtasks.
2. `_extract_field()` used a single-line regex; continuation lines on the
   next line were silently dropped, so the parsed `Goal` was already
   truncated before the user ever saw it.

**Hardening:**
- `max_tokens` raised to `8000`.
- `_extract_field()` rewritten to accumulate continuation lines up to the
  next labelled field (`Goal:`, `Files:`, `Tests:` …) or a blank line.
- `looks_truncated()` flags responses ending with a conjunction, colon,
  unclosed fence, or a too-short body, and `generate_with_validator()`
  retries once when truncation is detected.

**Status:** Hardened. Tested in
`tests/test_llm_hardening.py::TestMultilineFieldExtraction`.

---

## Summary table

| # | Feature | Severity | Status | Mechanism |
|---|---------|----------|--------|-----------|
| 1 | `prg design` empty criteria | Medium | Hardened | Validator-driven retry + partial salvage |
| 2 | `prg plan` under-decomposition | High | Hardened | `len(tasks) < 3` fallback trigger + min-count validator |
| 3 | `prg plan` hallucinated paths | High | Hardened | Tree injection + post-hoc path grounding |
| 4 | `prg plan` truncated text | High | Hardened | Multi-line extractor + truncation-aware retry |

---

## LLM-output hardening — what PRG does

`generator/ai/hardening.py` centralises the retry/validation layer used by
`DesignGenerator` and `TaskDecomposer`:

- **`looks_truncated(text)`** — heuristic detector for mid-sentence cuts
  (trailing conjunctions, unclosed code fences, punctuation-ending tails,
  below-minimum length).
- **`generate_with_validator(client, prompt, validator, ...)`** — single
  retry with a repair hint prepended to the prompt and temperature
  reduced by 0.3. SDK exceptions are caught and treated as invalid output.
- **`require_sections(*headings)` / `require_min_count(pattern, n)`** —
  ready-made validators for common structural checks.
- **`discover_source_dirs(project_path)`** — finds real top-level source
  directories, preferring the conventional `src/`, `lib/`, `app/` when they
  exist and falling back to any non-blocklisted dir containing Python, Go,
  or TypeScript files.
- **`ground_paths(paths, project_path)`** — rewrites hallucinated top-level
  directories to match the actual project layout, without dropping paths
  (dropping would hide bugs from the reviewer).

These utilities are module-level and callable from any generator that wants
the same guarantees.

---

## Architectural limitations

These are deliberate trade-offs that have not yet been closed. They are
not bugs per se — they are constraints that shape the quality ceiling of
AI-driven commands.

### SelfReviewer: suspicious-term detection is narrow

**Area:** `generator/planning/self_reviewer.py`

Uses a regex to find capitalised compound names and checks them against the
README. Won't catch hallucinated function names or subtle misinterpretations
that don't follow that naming pattern.

**Why this remains:** deterministic symbol-level checking requires an AST
cross-reference and a real symbol table. On the roadmap, not urgent.

### TaskDecomposer: structural fallback is coarse-grained

**Area:** `generator/tasks/decomposer.py` — `_tasks_from_design()`

When the LLM returns too few tasks, PRG falls back to a structural builder
that emits one task per architecture decision, one per data model, and one
per API contract. This is correctness-preserving but not semantically rich.

**Why this remains:** better decomposition means a more complex prompt
and higher failure rate. A deterministic floor is the safer default.

### Autopilot / Ralph: single-shot implementation

**Area:** `generator/ralph/engine.py` + `generator/planning/task_agent.py`

The agent is given a subtask and implements it in one LLM call; there is
no "draft a change plan before writing files" phase. Git branch isolation
limits the blast radius, but bad changes require manual triage.

**Why this remains:** a change-plan phase doubles LLM cost and latency;
the value depends on the quality of the plan/design, which is being
improved first.

### Large projects: context size

**Area:** `task_decomposer.py`, `self_reviewer.py`, `skill_generation.py`

Every LLM request sends the README, project tree, and previous artifacts.
On very large codebases this risks hitting the context window limit and
gets expensive.

**Why this remains:** selective context injection requires a retrieval layer
(embeddings or symbol index). In scope for a future release.

### No schema validation on LLM output

**Area:** all generators

Pydantic models exist for `Design`, `ArchitectureDecision`, `SubTask`, but
LLM output is parsed with regex rather than against the model schema. The
validator hooks in `hardening.py` give structural guarantees (section names
present, minimum count of task headings) but not type-level guarantees.

**Why this remains:** JSON-mode output is more brittle with smaller models
(Groq Llama 3.1 8B) than markdown is. The current compromise validates at
the structural level and salvages partial output when strict parsing fails.

---

## Reporting issues

If you encounter output quality problems that are not listed here, please
open an issue with:

1. The command you ran (`prg design ...` / `prg plan ...`).
2. The AI provider you used (Groq / Gemini / Anthropic / OpenAI).
3. The raw LLM response if you can capture it (add `--verbose`).
4. What you expected vs. what you got.

[Open an issue on GitHub](https://github.com/Amitro123/project-rules-generator/issues/new).

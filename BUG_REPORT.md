### Additional fix found during E2E (Bug B — second path)

`cli/skill_pipeline.py::_llm_generate_skills` was calling
`SkillPathManager.save_learned_skill`, writing new dirs into the global cache.

**Fix:** threaded `output_dir` through `_phase_skills → _auto_generate_skills →
_llm_generate_skills`, redirecting writes to
`<project>/.clinerules/skills/learned/<name>/SKILL.md`.

Every console line now ends with `(project-local)` — explicit confirmation that
zero writes hit the global cache.

### Regression suite

**1391 passed**, 11 skipped (8 new tests in `tests/test_bug_report_ai_flag.py`).

> **Lesson:** E2E validation on a real project surfaced a second pollution path
> that unit tests and fixtures missed. Always validate against a real project
> before closing a bug report.



---

## Bug F — "API key" warning printed once per skill instead of once per run

**Symptom:**
`Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.`
printed 7 times — once per LLM call — instead of once at startup.

**Fix:** Move the key-resolution warning to the provider initialization
(called once), not to the per-skill generation call.

**File:** `generator/ai/llm_skill_generator.py` or equivalent provider init

---

## Bug G — Generated file paths in console output are inconsistent

**Symptom:**
Skill generation lines print relative paths:
`💾 Generated: skills/learned/async-testing (project-local)`
But the final "Generated files:" block prints absolute paths:
`C:\Users\Dana\.gemini\...\clinerules.yaml`

**Fix:** Normalize all output paths to relative (relative to the analyzed
project root). Absolute paths leak local machine structure and are noisy
in CI logs.

**File:** `cli/analyze_cmd.py` or wherever the final file list is printed


---

## Bug H — Placeholder template leaked into project skill (passes Bug-C guard)

**Symptom:**
`skills/project/gemini-api/SKILL.md` contains unfilled template tokens:
description: |
[One sentence: what this skill does and when to activate it.]
...

Purpose
[One sentence: what problem does this solve and for whom.]
...

Process
1. [First step]
❌ [What NOT to do]

The file passes the Bug-C guard (`_is_meaningful_skill_content`) because it
has a `# heading` — but the content is unusable.

**Root cause:**
The project-skill generator (separate from `_llm_generate_skills`) falls back
to a raw stub template when no strategy produces real content. This path does
not run through the LLM/cowork chain, so bracketed tokens are never filled.

**Repro:**
```bash
prg analyze . --ai --ide antigravity
```
On a project with a real README but no `pyproject.toml`, `requirements.txt`,
or `package.json` (e.g., `hermes-skills`).

**Fix options (in order of preference):**
1. Extend `_is_meaningful_skill_content` to reject files where bracketed
   placeholder density exceeds a threshold:
   `re.findall(r'\[[^\]]{3,}\]', content)` → reject if count > 2
2. Ensure the project-skill generator routes through the LLM strategy before
   falling back to the stub — the README was 2,883 bytes, enough context
3. If stub fallback is unavoidable, fill brackets with detected project facts
   rather than leaving them literal

**Files:**
- `generator/skill_generator.py` — `_is_meaningful_skill_content`
- whichever strategy writes the project-skill stub (needs investigation)

**Regression test:**
```python
def test_placeholder_content_rejected():
    content = "# Skill\n## Purpose\n[One sentence: what this does]"
    assert not _is_meaningful_skill_content(content)
```

Please fix the following bugs in priority order.
Do not move to the next bug until the current one is fixed and tested.

---

### Priority 1 — Bug H (placeholder leak)

`_is_meaningful_skill_content` must reject content containing bracketed
placeholder tokens. Add this check:

```python
import re
placeholder_matches = re.findall(r'\[[^\]]{3,}\]', content)
if len(placeholder_matches) > 2:
    return False
```

Then trace which strategy writes the stub for projects with no build markers
(no pyproject.toml / requirements.txt / package.json) and ensure it routes
through the LLM before falling back.

Regression test: `test_placeholder_content_rejected` in
`tests/test_bug_report_ai_flag.py`.

---

### Priority 2 — Bug F (API key warning repeated per skill)

The warning `Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.`
is printed once per LLM call. Move it to provider initialization so it prints once.

---

### Priority 3 — Bug G (absolute paths in console output)

Normalize all printed file paths to relative (relative to the analyzed
project root).

---

After all three are fixed, run:
```bash
prg analyze . --ai --ide antigravity
```
on `hermes-skills` and confirm:
1. `gemini-api/SKILL.md` contains real content (no bracketed tokens)
2. API key warning appears exactly once
3. All printed paths are relative

Report suite count after each fix.

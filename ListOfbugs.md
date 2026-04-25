# hermes-skills Quality Audit — Bug Tracker

Verified by re-running `prg analyze . --ai --ide antigravity` on hermes-skills
after commit `3a2f214` (fix: resolve 8 bugs from hermes-skills quality audit).

---

## Output file status

| File | Status after re-run |
|---|---|
| `.clinerules/clinerules.yaml` | ✅ `skills.project` key present; `total: 3` |
| `.clinerules/rules.md` | ✅ Safety rules mined; all 5 priorities present (but items 6-7 wrong — see R1) |
| `.clinerules/rules.json` | ✅ Clean `critical_antipatterns_never_do_this` key; no YAML fragments |
| `.clinerules/auto-triggers.json` | ✅ Filtered to 1 group (`gemini-api` only) |
| `.clinerules/skills/index.md` | ⚠️ Stale placeholder text (see M1) |
| `.clinerules/skills/project/gemini-api/SKILL.md` | ✅ Real content, no placeholders |
| `.agents/rules/hermes-skills.md` | ✅ Mirrors rules.md (accepted) |

---

## ✅ VERIFIED FIXED

### C1. rules.json garbage anti-patterns key — FIXED ✅

**Root cause:** The md→json converter scraped every bullet under a `##` heading,
including YAML content embedded in a `<!-- ... -->` HTML comment that followed the
anti-patterns heading. The key was sluggified with emoji/parens.

**Fix (`generator/rules_generator.py`):**
- Parser resets `current_section = None` on lines starting with `<!--`, stopping
  bullet collection before any embedded YAML block.
- Key normalization: `re.sub(r"[^\w\s]", "", ...).lower().strip()` then
  `re.sub(r"\s+", "_", ...)` strips emoji/parens before snake_casing.

**Verified:** Key is now `critical_antipatterns_never_do_this` with only 2 entries.

---

### C2. auto-triggers.json polluted with 20+ irrelevant triggers — FIXED ✅

**Root cause:** `save_triggers_json()` called `extract_all_triggers()` which walks
every globally-available skill (builtin + learned global cache), not just the
skills selected for this project.

**Fix (`generator/skills_manager.py`, `cli/analyze_pipeline.py`):**
- `save_triggers_json(output_dir, include_only=None)` delegates to
  `extract_project_triggers(include_only=...)` instead of `extract_all_triggers()`.
- `_phase_write_rules()` threads the `include_only` whitelist through.
- Call site passes `enhanced_selected_skills` through to `save_triggers_json`.

**Verified:** Down from 37 trigger groups to 1 (`gemini-api`).

---

### C3. Project skill missing from clinerules.yaml / skills/index.md — FIXED ✅

**Root cause:** `generate_clinerules()` only recognised `builtin/` and `learned/`
refs; `project/` refs were silently dropped. `_auto_generate_skills()` never added
existing project-local skills to the selection set.

**Fix (`generator/outputs/clinerules_generator.py`, `cli/skill_pipeline.py`):**
- `generate_clinerules()` emits `skills.project` list and updates `skills_count`.
- `_auto_generate_skills()` appends `project/<name>` refs for existing project-local
  skills to `enhanced_selected_skills`.

**Verified:** `clinerules.yaml` now has `skills.project: [skills/project/gemini-api/SKILL.md]`
and `skills_count: {project: 1, builtin: 2, learned: 0, total: 3}`.

---

### H2. DO/DON'T rules generic API advice, not Hermes-specific — FIXED ✅

**Root cause:** `extract_conventions()` missed "Safety First" / "Principles" headers.

**Fix (`generator/analyzers/readme_parser.py`):**
- Added `"safety"`, `"safety first"`, `"principles"`, `"constraints"`, `"never do"`,
  `"do not"`, `"always"`, `"must"` to `convention_headers`.

**Verified:** `rules.md` now has `**README Conventions:**` block with all 4 hermes-specific
safety rules (no restart if in-place fix possible, read before rewrite, validate YAML,
prefer `docker restart` over full stack).

---

### M2. gemini-api/SKILL.md truncated mid-code-block — FIXED ✅

**Root cause:** `max_tokens=2000` hit before closing the final code block.

**Fix (`cli/skill_pipeline.py`):** `max_tokens` raised from `2000` to `4000`.

**Verified:** SKILL.md contains full content with no mid-block truncation.

---

## ✅ FIXED — R1/R2/R3 (verified after second re-run)

### R1 (was H3). Priorities 6–7 scrape port numbers instead of steps — FIXED ✅

**Severity:** High — agent reads `**8642**: Hermes Gateway + API` as a workflow
priority instead of a service port.

**Observed output (`rules.md`):**
```
1. Diagnose: Read logs/config first.
2. Plan: Show exact changes before acting.
3. Confirm: Get explicit approval for destructive actions.
4. Execute: Minimal, idempotent commands.
5. Verify: Always check health/logs after change.
6. **8642**: Hermes Gateway + API         ← WRONG: this is a port mapping
7. **3001**: Workspace UI (Vite)          ← WRONG: this is a port mapping
```

**Root cause:** `features[:3]` was raised to `features[:7]`, but the priority
extractor didn't stop at section boundaries. After the 5 real priorities it fell
through into "Key Service Ports" and scraped bold port entries as steps.

**Fix (`generator/rules_sections/templates.py`):**
- Added `import re` to the module.
- Pre-filter `features` with `_port_re = re.compile(r"^\*{0,2}\d+\*{0,2}\s*:")` before
  slicing. Any item whose stripped text begins with a bold-or-bare integer followed
  by a colon (e.g. `**8642**: Hermes Gateway`) is excluded.

**Verified:** Priorities 1–5 are the exact Operational Model steps; items 6–7 are
safety rules from the "Safety First" section (meaningful, not port numbers).

---

### R2 (was C4). project_type stays python-cli despite agent_skills scoring 1.1 — FIXED ✅

**Root cause (`generator/parsers/enhanced_parser.py:363`):**
`_newer_only_uncertain = {"agent", "generator", "web-app"}` — `"agent-skills"` was
missing. The override gate only fired when StructureAnalyzer returned
`library`/`unknown`, but hermes-skills got `python-cli`, so `agent_skills` (scored
1.1) was silently ignored.

**Fix (`generator/parsers/enhanced_parser.py`):**
- Added `_always_override = {"agent-skills"}` set.
- New branch before the `_newer_only_uncertain` gate:
  ```python
  elif _newer_type in _always_override and _newer_confidence >= 0.8:
      project_type = _newer_type
  ```
  `agent-skills` is structurally distinct (SKILL.md-only repo, no Python sources)
  — the newer detector is always more accurate than StructureAnalyzer here.

**Verified:** `clinerules.yaml` now shows `project_type: agent-skills`.

---

### R3 (was H1). Tech stack shallow — pipeline bypassed the updated detector — FIXED ✅

**Root cause:** Two separate tech-detection code paths existed:

| Path | Returns for hermes-skills |
|---|---|
| `readme_parser.extract_tech_stack()` → CLI pipeline → `clinerules.yaml` | `['gemini']` |
| `tech_detector.detect_tech_stack()` → skills generation only | `['docker', 'telegram', 'gemini', 'linux', 'vite', 'yaml']` |

The H1 fix only updated `tech_detector`. `enhanced_parser.py` supplemented from
README using only a hardcoded CDN-tech allowlist (konva, canvas, dxf, supabase…)
that excluded infrastructure techs entirely.

**Fix (`generator/parsers/enhanced_parser.py`):**
- Replaced the narrow `detect_from_readme` + `readme_primary` filter with a call
  to `detect_tech_stack(self.path, readme_content=raw_readme)`.
- This single call handles CDN techs, infrastructure-category techs (docker,
  telegram, linux, yaml, vite), AND the `allow_all_from_readme` fallback for
  projects with no dep files — all in one pass.

**Verified:** `clinerules.yaml` now shows:
```yaml
tech_stack: ['docker', 'gemini', 'linux', 'telegram', 'vite', 'yaml']
```

---

## ✅ FIXED — M1 / H4

### M1. skills/index.md stale placeholder — FIXED ✅

`index.md` no longer contains "Load skills from hermes-skills-skills.md".

**Fix (`generator/renderers.py`):** Updated USAGE section in `MarkdownSkillRenderer`
to reference `.clinerules/skills/index.md` instead of `{project}-skills.md`.

**Fix (`cli/analyze_pipeline.py`):** `generate_perfect_index` now overwrites the
renderer output entirely — the USAGE section is not emitted at all in the
Perfect Format output, so the stale placeholder cannot reappear.

**Verified:** `"hermes-skills-skills.md"` is absent from the generated index.md.

---

### H4. skills/index.md lists different skills than clinerules.yaml — FIXED ✅

**Root cause:** `_run_skill_orchestration` (legacy path) wrote `skills/index.md`
using its own orchestrator skill selection, completely independent of
`enhanced_selected_skills` (which drives `clinerules.yaml`). Result: different
skills appeared in each file.

**Fix (`generator/skills_manager.py`):**
- Added `include_only: Optional[Set[str]] = None` parameter to
  `generate_perfect_index`.
- When supplied, non-project skills are filtered to those whose name matches any
  ref in `include_only` (name-only match, so `"builtin/code-review"` in the set
  matches `"learned/code-review"` from `list_skills()` when the learned layer
  shadows the builtin).
- Project-local skills always shown regardless.

**Fix (`cli/analyze_pipeline.py`):**
- After `_run_skill_orchestration`, call `skills_manager.generate_perfect_index(
  project_type=project_type_label, include_only=enhanced_selected_skills)` to
  overwrite `index.md` with the consistent, filtered version.

**Verified (`clinerules.yaml` vs `index.md` after re-run):**

`clinerules.yaml` skills:
- `[project]` docker-deployment, gemini-api
- `[builtin]` code-review, systematic-debugging

`skills/index.md` sections:
- `### BUILTIN SKILLS` → systematic-debugging
- `### LEARNED SKILLS` → code-review *(shadows builtin — correct by priority)*
- `### PROJECT SKILLS` → docker-deployment, gemini-api

All 4 selected skills appear in both files. ✅

---

## ⚠️ REMAINING / Out-of-scope

| # | Bug | Status |
|---|---|---|
| M3 | `.clinerules/rules.md.bak` / `rules.json.bak` left behind | Low priority — add to generated `.gitignore` in a follow-up |
| M4 | `~/.project-rules-generator/learned/` has test-suite pollution (`b.md`, `ai-test-skill/`, `existing-skill/`, etc.) | Needs conftest.py `$HOME` override; tracked separately |

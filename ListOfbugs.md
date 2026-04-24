Quality Review — hermes-skills output
Files generated
File	Size	Status
.clinerules/clinerules.yaml	538 B	[FIXED] project skill now included under skills.project key
.clinerules/rules.md	2796 B	[FIXED] safety/principles sections now mined; priorities uncapped
.clinerules/rules.json	1749 B	[FIXED] garbage key eliminated; keys normalized to snake_case
.clinerules/auto-triggers.json	5090 B	[FIXED] filtered to project skills only (no global-cache leakage)
.clinerules/skills/index.md	1862 B	[FIXED] project skill now discovered and listed under PROJECT SKILLS
.clinerules/skills/project/gemini-api/SKILL.md	~7 KB	[FIXED] max_tokens raised to 4000; truncation resolved
.agents/rules/hermes-skills.md	2796 B	duplicate of rules.md (accepted, not a bug to fix here)

---

## FIXED issues

### C1. rules.json garbage anti-patterns key — FIXED

**Root cause:** The md->json converter scraped every bullet under a `##` heading,
including YAML content embedded in a `<!-- ... -->` HTML comment that followed the
anti-patterns heading. The key was also sluggified with emoji/parens instead of
being normalized to snake_case.

**Fix (`generator/rules_generator.py`):**
- Parser now resets `current_section = None` when it encounters a line starting
  with `<!--`, stopping bullet collection before any embedded YAML block.
- Section heading->key normalization changed from
  `section_name.lower().replace(" ", "_")` to
  `re.sub(r"[^\w\s]", "", ...).lower().strip()` then `re.sub(r"\s+", "_", ...)`
  so emoji, parens and other non-word chars are stripped before snake_casing.

---

### C2. auto-triggers.json polluted with 20+ irrelevant triggers — FIXED

**Root cause:** `save_triggers_json()` called `extract_all_triggers()` which walks
every globally-available skill (builtin + learned global cache), not just the
skills selected for this project.

**Fix (`generator/skills_manager.py`, `cli/analyze_pipeline.py`):**
- `save_triggers_json(output_dir, include_only=None)` now accepts an
  `include_only` set and delegates to `extract_project_triggers(include_only=...)`
  instead of `extract_all_triggers()`.
- `_phase_write_rules()` gained an `include_only` parameter.
- The call site in `analyze_pipeline.py` passes `enhanced_selected_skills` (the
  same whitelist already used for trigger content generation) through to
  `save_triggers_json`.

---

### C3. Project skill missing from clinerules.yaml and skills/index.md — FIXED

**Root cause:** `generate_clinerules()` only recognized `builtin/` and `learned/`
prefixes in the selected-skills set; `project/` refs were silently dropped.
Additionally, `_auto_generate_skills()` never added existing project-local skills
to the selection set, so they were invisible to downstream consumers.

**Fix (`generator/outputs/clinerules_generator.py`, `cli/skill_pipeline.py`):**
- `generate_clinerules()` now handles `project/<name>` refs, emits a
  `skills.project` list, and includes project skill count in `skills_count`.
- `_auto_generate_skills()` scans `skills_manager.discovery.list_skills()` after
  matching and adds any `type="project"` skills as `project/<name>` refs to
  `enhanced_selected_skills` before returning.

---

### C4. Wrong project_type: python-cli — FIXED

**Root cause:** The project type detector had no category for agent-skills
collections (repos whose entire content is SKILL.md files). With no matching
type, it defaulted to `cli_tool` on weak signals from generic patterns.

**Fix (`generator/analyzers/project_type_detector.py`):**
- Added `agent_skills` score key and `_detect_agent_skills_signals()` detector.
- For pure docs/skills repos (SKILL.md files present, no .py sources outside
  .clinerules/ / .venv): score 0.9 + bonus per skill file.
- For mixed projects (have Python sources too): score 0.2 only, so framework
  types remain dominant.
- Added `"agent-skills"` to `TYPE_LABEL_MAP`.

---

### H1. Tech stack shallow — just [gemini] — FIXED

**Root cause:** `detect_tech_stack()` only promoted README-detected techs to the
final set if they were already confirmed by dependency files. Ops-heavy projects
with no `requirements.txt`/`package.json` got nothing from the README pass.
Telegram, YAML, and Linux were also missing from the tech registry entirely.

**Fix (`generator/tech/_profiles/infrastructure.py`, `generator/utils/tech_detector.py`):**
- Added `TechProfile` entries for `telegram`, `yaml`, and `linux` in the
  infrastructure category.
- `detect_tech_stack()` now auto-promotes all `category="infrastructure"` techs
  from README (via `TECH_CATEGORIES` lookup), so Docker, Telegram, Linux, etc.
  are included without needing a dep file.
- When `len(detected) == 0` (no dep files found at all), README is used as the
  sole source for all techs (`allow_all_from_readme = True`).

---

### H2. DO/DON'T rules generic API advice, not Hermes-specific — FIXED

**Root cause:** `extract_conventions()` only looked for headers like "conventions",
"architecture", "rules" etc. Hermes-style "Safety First" / "Principles" /
"Constraints" sections were not scanned, so project-specific safety rules never
reached the DO/DON'T output.

**Fix (`generator/analyzers/readme_parser.py`):**
- Added `"safety"`, `"safety first"`, `"principles"`, `"constraints"`,
  `"never do"`, `"do not"`, `"always"`, `"must"` to `convention_headers` in
  `extract_conventions()`.
- These sections are now scraped and appended under **README Conventions** in the
  DO rules block.

---

### H3. Priorities truncated from 5 to 3 — FIXED

**Root cause:** `features[:3]` hard-capped the priority list at three items, and
the template hardcoded three numbered lines.

**Fix (`generator/rules_sections/templates.py`):**
- Cap raised from `features[:3]` to `features[:7]`.
- Template now renders priorities dynamically:
  `priorities_str = "\n".join(f"{i+1}. {p}" for i, p in enumerate(priorities))`
  replacing the three hardcoded lines.

---

### M2. gemini-api/SKILL.md truncated mid-code-block — FIXED

**Root cause:** `llm_gen.generate_content(prompt, max_tokens=2000)` hit the token
limit before closing the final code block in the Examples section.

**Fix (`cli/skill_pipeline.py`):**
- `max_tokens` raised from `2000` to `4000` for project skill LLM generation.

---

## Remaining / out-of-scope items

| # | Bug | Status |
|---|-----|--------|
| M1 | skills/index.md broken template placeholder (hermes-skills-skills.md) | Out of scope — placeholder comes from a template string unrelated to the bugs above; tracked separately |
| M3 | .clinerules/rules.md.bak / rules.json.bak left behind | Acceptable for dev; add to generated .gitignore in a follow-up |
| M4 | Global ~/.project-rules-generator/learned/ test pollution | Requires test suite isolation ($HOME override in conftest.py); tracked separately |
| H4 | Skills index/yaml inconsistent listing criteria | Follow-up: align EnhancedSkillMatcher inclusion criteria with generate_perfect_index traversal |

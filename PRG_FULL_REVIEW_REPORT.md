# Full Review Report

Here's the complete analysis from both the code deep-dive and the Anthropic PDF comparison.

## ✅ Resolution Summary (updated after implementation)

| Item | Status | Notes |
|------|--------|-------|
| BUG-A1 — READMEStrategy dead | ✅ Fixed | Path/content normalization applied in prior session |
| BUG-A2 — detect_skill_needs 7 techs | ✅ Fixed | Now delegates to `SkillGenerator.TECH_SKILL_NAMES` (40+) |
| BUG-A3 — adapt pollutes global learned | ✅ Fixed | BUG-B fix: project-specific content no longer written to global cache |
| BUG-A4 — Dual _validate_quality systems | ✅ Fixed | DESIGN-B fix: `_validate_quality` delegates to `quality_checker.validate_quality()` |
| BUG-A5 — quality_score: 95 hardcoded | ✅ Fixed | BUG-C fix: removed `{{ quality_score }}` from Jinja2 template |
| GAP-1 — YAML frontmatter schema | ✅ Fixed | All 4 strategies emit Anthropic-spec frontmatter |
| GAP-2 — Semantic description-based triggering | ✅ Fixed | "Use when user mentions..." pattern in all frontmatter |
| GAP-3 — Monolithic file / progressive disclosure | ✅ Fixed | `scripts/`, `references/`, `assets/` scaffolded on `create_skill()` |
| GAP-4 — No scripts/references/assets support | ✅ Fixed | Same as GAP-3 |
| GAP-5 — No negative triggers, no ## CRITICAL | ✅ Fixed | Negative triggers in description + `## CRITICAL` section in template |
| GAP-6 — Structural-only quality gates | ✅ Fixed | `TriggerEvaluator` with precision scoring |
| GAP-7 — No MCP metadata | ⚠️ Partial | `allowed-tools` added; `mcp-server` skipped (requires project-specific info) |

---

## 🔴 Part A — 5 New Bugs Found (Post v1.2)

### BUG-A1 — READMEStrategy is Completely Dead (Silent No-op)
**File:** `generator/strategies/readme_strategy.py`

This is the most critical silent failure in the codebase. `SkillGenerator.create_skill()` passes `from_readme` as a string of README content, but `READMEStrategy.generate()` immediately does `Path(from_readme)` and calls `.exists()` on it. A multi-line content string will never be a valid file path, so the condition is always False — the strategy always returns None and falls through.

```python
# CURRENT — broken
readme_path = Path(from_readme)   # ← content string, not a path
if not readme_path.exists():       # ← always False → always skips
    return None
```
The entire READMEStrategy path has been dead since it was written. Every `--from-readme` call silently falls through to CoworkStrategy.

### BUG-A2 — DESIGN-3 Test Exists, Fix Was Never Applied
**File:** `generator/skill_creator.py`

`detect_skill_needs()` has a `tool_map` with only 7 entries while `SkillGenerator.TECH_SKILL_NAMES` maps 40+ technologies. The v1.2 regression test (DESIGN-3) documents this gap, but the actual code fix was never merged. Technologies like openai, langchain, redis, supabase, pydantic, konva are completely invisible to `generate_all()`.

`TECH_SKILL_NAMES`: 40+ techs  ←→  `detect_skill_needs tool_map`: 7 techs

### BUG-A3 — adapt Branch Pollutes Global Learned with Project-Specific Content
**File:** `generator/skill_generator.py`

In `generate_from_readme()`, the `adapt` branch writes project-specific skill content (containing the project name, README excerpts, specific paths) back into `~/.project-rules-generator/learned/`. The next project that reuses that global skill inherits Project A's context — a cross-project contamination bug.

```python
# BAD — project-specific content written to global
resolved.write_text(skill_content, encoding="utf-8")  # ← pollutes global cache
```

### BUG-A4 — Dual _validate_quality Systems with Divergent Logic
**Files:** `skill_creator.py` + `utils/quality_checker.py`

DESIGN-1 in v1.2 unified the QualityReport dataclass, but the quality logic is still duplicated in two places with different thresholds. `skill_creator._validate_quality()` doesn't call `quality_checker.validate_quality()` at all, so a skill can pass one system and silently fail the other.

| Check | `_validate_quality()` | `validate_quality()` |
|---|---|---|
| Required sections | ❌ | ✅ |
| Stub markers | ❌ | ✅ |
| Trigger threshold | < 3 (-5pts) | < 2 (-10pts) |
| Hallucinated paths | ✅ | ❌ |

### BUG-A5 — quality_score: 95 Hardcoded in Jinja2 Context
**File:** `generator/skill_creator.py`

Quality is computed after content generation. But `_generate_with_jinja2()` passes `quality_score: 95` into the template context before any quality check runs. Any template rendering `{{ quality_score }}` always shows 95.

## 🟠 Part B — 7 Alignment Gaps vs Anthropic's Official Skill Standard

### GAP-1 🔴 — YAML Frontmatter Schema Mismatch (High)
Your generated frontmatter uses non-standard fields (`auto_triggers`, `tools`, `category`) and is missing the officially required ones. The most critical: `description` must contain the trigger conditions in a "Use when..." format and must stay under 1024 characters.

| Field | Official Standard | PRG |
|---|---|---|
| description | What + "Use when..." + <1024 chars, no XML | Short descriptor, no trigger pattern |
| allowed-tools | ✅ Supported | ❌ Missing |
| compatibility | ✅ Supported | ❌ Missing |
| license | ✅ Supported | ❌ Missing |
| auto_triggers | ❌ Not standard | ✅ PRG-only |

### GAP-2 🔴 — Keyword-Array Triggers vs. Semantic Description-Based Triggering (High)
PRG's `auto-triggers.json` + `## Auto-Trigger` section is a homegrown keyword-matching system. The official mechanism is the `description` field itself, where Claude's LLM semantically decides when to load a skill. PRG skills generated without the "Use when..." pattern in `description` simply won't auto-trigger when uploaded to Claude.

This is the most impactful gap for end-user value. Skills generated by PRG won't work natively in Claude unless `description` follows the official format.

### GAP-3 🟡 — Monolithic Skill File vs. 3-Level Progressive Disclosure (Medium)
The official standard uses a 3-level context loading system to optimize tokens:

| Level | What loads | When |
|---|---|---|
| Frontmatter | Always, every turn | Minimal token cost |
| `SKILL.md` body | When Claude deems relevant | On-demand |
| `references/` files | When explicitly needed | Lazy-loaded |

PRG generates a single monolithic `.md` file with everything embedded. This means all verbose context (README quotes, key file excerpts) loads at once. Splitting these into a `references/` subfolder would dramatically reduce token burn per conversation.

### GAP-4 🟡 — No scripts/, references/, assets/ Subdirectory Support (Medium)
The official skill folder supports bundling:

- `scripts/` — Python/Bash workflows Claude can execute
- `references/` — large docs loaded lazily
- `assets/` — templates, icons

PRG's `SkillDiscovery` only scans for `.md`/`.yaml`/`.yml` files and ignores everything else. Generated skills can't include runnable code or deferred documentation.

### GAP-5 🟡 — No Negative Triggers, No ## CRITICAL Section (Medium)
Two official patterns for reliability that PRG doesn't implement:

- **Negative triggers in description:** "Do NOT use for JavaScript or frontend reviews" — prevents over-triggering
- **## CRITICAL section:** Forces Claude to pay attention to non-negotiable rules

Neither is in PRG's Jinja2 template, `_generate_inline()`, or `_validate_quality()`.

### GAP-6 🟡 — Quality Gates Are Structural Only, No Runtime Behavioral Checks (Medium)

| Official Benchmark | PRG Equivalent |
|---|---|
| Triggers on ≥90% of relevant queries | ❌ None |
| 0 failed API calls per workflow | ❌ None |
| Doesn't trigger on irrelevant queries | ❌ None |
| Completes without user correction | ❌ None |

PRG checks structure (does the file have `## Purpose?`). The official standard checks behavior (does it actually work?). A `prg test-skill <name>` command with light LLM-based trigger testing would close this gap.

### GAP-7 🟢 — No MCP Metadata Support (Low)
Generated frontmatter doesn't emit `mcp-server` metadata or `allowed-tools` field, blocking teams that need MCP-integrated workflows.

## 🗺️ Recommended Fix Priority

### WEEK 1 — Critical Bugs
- **BUG-A1:** Fix READMEStrategy path/content mismatch
- **BUG-A3:** Guard against global-learned pollution in adapt branch
- **BUG-A2:** Expand `detect_skill_needs()` tool_map from TECH_SKILL_NAMES

### WEEK 2 — Schema & Trigger Alignment
- **GAP-1:** Add description format validation (1024-char, "Use when...", no XML)
- **GAP-2:** Merge auto_triggers into description for Claude-native triggering
- **GAP-5:** Add negative trigger support + `## CRITICAL` template section

### WEEK 3 — Architecture
- **GAP-3:** Introduce `references/` subdirectory for progressive disclosure
- **GAP-4:** Add `scripts/` and `assets/` to SkillDiscovery scanner
- **BUG-A4:** Consolidate `_validate_quality` to delegate to `quality_checker`

### FUTURE
- **GAP-6:** `prg test-skill` command with trigger-rate testing
- **GAP-7:** MCP metadata fields

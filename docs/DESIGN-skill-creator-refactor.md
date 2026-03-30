# DESIGN: Refactor `generator/skill_creator.py` (God-Module Decomposition)

**Branch:** `refactor/god-modules-skill-creator`
**Status:** In Progress
**Size before:** 1190 LOC → **target:** ~250 LOC orchestrator + 3 focused modules

---

## Problem

`generator/skill_creator.py` is a 1190-line god-module. It mixes four unrelated concerns:
1. Metadata construction (triggers, tags, tools, frontmatter)
2. Documentation discovery and loading
3. Content generation (AI, Jinja2, inline)
4. Quality validation and hallucination detection

This makes the file hard to read, test in isolation, and extend.

---

## Solution: Extract 3 Helper Modules

Keep `CoworkSkillCreator` and `SkillMetadata` in `skill_creator.py` (backwards compatibility — tests import from there). Extract internal responsibilities into focused helper classes.

```
generator/
├── skill_creator.py              # Thin orchestrator (~250 LOC)  ← unchanged public API
├── skill_quality_validator.py    # NEW: quality gates + hallucination detection (~90 LOC)
├── skill_doc_loader.py           # NEW: supplementary doc discovery + loading (~120 LOC)
└── skill_metadata_builder.py     # NEW: metadata, triggers, tools, frontmatter (~320 LOC)
```

---

## Module Boundaries

### `skill_quality_validator.py` — `SkillQualityValidator`

**Responsibility:** Validate skill content quality; detect hallucinated paths; auto-fix common issues.

**Moved from `CoworkSkillCreator`:**
- `_validate_quality(content, metadata) → QualityReport`
- `_detect_hallucinated_paths(content) → List[str]`
- `_auto_fix_quality_issues(content, quality) → str`

**Constructor:** `SkillQualityValidator(project_path: Path)`

---

### `skill_doc_loader.py` — `SkillDocLoader`

**Responsibility:** Discover and load supplementary project documentation for LLM context.

**Moved from `CoworkSkillCreator`:**
- `SUPPLEMENTARY_BUDGET = 1500` (class constant)
- `_DOCS_SKIP` (class constant set)
- `_DOCS_HIGH_VALUE` (class constant set)
- `_score_doc(path, content) → int`
- `_discover_supplementary_docs() → List[Path]`
- `_load_key_files(skill_name) → Dict[str, str]`

**Constructor:** `SkillDocLoader(project_path: Path)`

---

### `skill_metadata_builder.py` — `SkillMetadataBuilder`

**Responsibility:** Build `SkillMetadata` — triggers, tools, tags, frontmatter rendering.

**Moved from `CoworkSkillCreator`:**
- `TRIGGER_SYNONYMS` (class constant dict)
- `_build_metadata(skill_name, readme_content, tech_stack) → SkillMetadata`
- `_generate_triggers(skill_name, readme_content, tech_stack) → List[str]`
- `_extract_action_triggers(readme_content, skill_base) → Set[str]`
- `_select_tools(skill_name, tech_stack) → List[str]`
- `_validate_tools_availability(tools) → Set[str]`
- `_generate_description(skill_name, readme_content) → str`
- `_generate_negative_triggers(skill_name, tech_stack) → List[str]`
- `_generate_tags(skill_name, tech_stack) → List[str]`
- `_generate_critical_rules(skill_name, tech_stack) → List[str]`
- `_render_frontmatter(metadata) → str`

**Constructor:** `SkillMetadataBuilder(project_path: Path)`

---

## Backwards Compatibility Rules

1. `from generator.skill_creator import CoworkSkillCreator` — **must keep working**
2. `from generator.skill_creator import SkillMetadata` — **must keep working**
3. `from generator.skill_creator import QualityReport` — **must keep working** (re-export)
4. All public methods on `CoworkSkillCreator` unchanged (signature + return type)
5. Helper classes are **internal** — not part of the public API, no need to export from `skill_creator.py`

---

## `CoworkSkillCreator` After Refactor (~250 LOC)

```python
class CoworkSkillCreator:
    TECH_TOOLS = _TECH_TOOLS          # keep (used by strategies)
    PROJECT_SIGNALS = {...}            # keep (used by _detect_project_signals)

    def __init__(self, project_path):
        self.project_path = project_path
        self._detected_signals = None
        self._tech_stack = None
        self.discovery = SkillDiscovery(project_path)
        # New helper instances:
        self._quality = SkillQualityValidator(project_path)
        self._doc_loader = SkillDocLoader(project_path)
        self._metadata_builder = SkillMetadataBuilder(project_path)

    # All public methods kept, delegating internally:
    def create_skill(...) → delegates to helpers
    def auto_generate_skills(...)
    def detect_skill_needs(...)
    def exists_in_learned(...)
    def save_to_learned(...)
    def link_from_learned(...)
```

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Test imports break | `SkillMetadata`, `CoworkSkillCreator`, `QualityReport` stay in `skill_creator.py` |
| Circular imports | Helper modules only import from `generator.utils.*` and stdlib — no back-imports to `skill_creator` |
| `_detect_tech_stack` shared state | Keep `_detect_tech_stack` + `_detect_project_signals` on `CoworkSkillCreator`; pass results to `SkillMetadataBuilder.build_metadata()` as arguments |
| `_generate_content` not extracted | Kept in `CoworkSkillCreator` — it's a thin router (AI → Jinja2 → inline) and tightly coupled to `SkillDocLoader._load_key_files` |

---

## Implementation Order

1. Extract `SkillQualityValidator` (smallest, most self-contained)
2. Extract `SkillDocLoader` (medium, no dependencies on other helpers)
3. Extract `SkillMetadataBuilder` (largest, depends on `TECH_TOOLS` from `tech_registry`)
4. Run `pytest` — must pass 553+ tests with zero regressions

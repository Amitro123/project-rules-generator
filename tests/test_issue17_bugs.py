"""
Tests for Issue #17 — Skills Mechanism Code Review
====================================================
Covers all 5 bugs and 3 design issues that needed new test coverage.

BUG-1: Missing f-prefix in _validate_quality warning
BUG-2: Dead code readme_content.lower() in _detect_from_readme
BUG-3: Wrong path for flat-file skills in SkillGenerator.create_skill()
BUG-4: Silent skill loss when resolve_skill returns None in generate_from_readme
BUG-5: CoworkStrategy hardcodes use_ai=True

DESIGN-3: detect_skill_needs() tool_map coverage vs TECH_SKILL_NAMES
DESIGN-4: _skills_cache never invalidated after creating a new skill
DESIGN-1: QualityReport should come from one source (quality_checker)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generator.skill_creator import CoworkSkillCreator, SkillMetadata
from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator


# ---------------------------------------------------------------------------
# BUG-1: f-string missing — warning must show actual count, not literal text
# ---------------------------------------------------------------------------


def test_validate_quality_warning_shows_actual_count(tmp_path):
    """BUG-1: _validate_quality warning must interpolate trigger count, not print literal."""
    creator = CoworkSkillCreator(tmp_path)

    # Skill with exactly 1 trigger (< 3 threshold)
    metadata = SkillMetadata(
        name="test-skill",
        description="test",
        auto_triggers=["one trigger"],
        tools=["pytest"],
    )
    content = "```bash\npytest\n```"
    quality = creator._validate_quality(content, metadata)

    # Find the trigger warning
    trigger_warnings = [w for w in quality.warnings if "trigger" in w.lower()]
    assert trigger_warnings, "Expected a trigger count warning"
    warning_text = trigger_warnings[0]

    # Must contain the actual number "1", NOT the literal "{len(..."
    assert "1" in warning_text, f"Warning should contain actual count '1', got: {warning_text!r}"
    assert "{len" not in warning_text, f"Warning must not contain un-interpolated f-string: {warning_text!r}"


# ---------------------------------------------------------------------------
# BUG-2: Dead code — _detect_from_readme must still detect tech correctly
# ---------------------------------------------------------------------------


def test_detect_from_readme_detects_tech_in_section(tmp_path):
    """BUG-2: After removing the no-op readme_content.lower(), detection must still work."""
    creator = CoworkSkillCreator(tmp_path)

    readme = """
# My Project

## Tech Stack
- FastAPI for REST endpoints
- PostgreSQL as the database
- Redis for caching
"""
    detected = creator._detect_from_readme(readme)
    assert "fastapi" in detected
    assert "postgresql" in detected
    assert "redis" in detected


def test_detect_from_readme_detects_tech_in_bullets_outside_section(tmp_path):
    """BUG-2: Tech in bullet points outside a tech-stack section must also be detected."""
    creator = CoworkSkillCreator(tmp_path)

    readme = """
# Project

Some description here.

- Uses pytest for testing
- Uses docker for deployment
"""
    detected = creator._detect_from_readme(readme)
    assert "pytest" in detected
    assert "docker" in detected


# ---------------------------------------------------------------------------
# BUG-3: Flat-file skills return wrong directory from create_skill()
# ---------------------------------------------------------------------------


def test_create_skill_flat_file_returns_correct_dir(tmp_path):
    """BUG-3: For flat-file skills (learned/myskill.md), create_skill must return
    learned/myskill/ — not the parent learned/ directory."""
    # Set up a fake global structure
    global_learned = tmp_path / "learned"
    global_learned.mkdir()

    # Create a flat-file skill (NOT directory-style)
    flat_skill = global_learned / "myskill.md"
    flat_skill.write_text("# My Skill\n\nContent here.", encoding="utf-8")

    discovery = SkillDiscovery(skills_dir=tmp_path)
    discovery.global_learned = global_learned
    discovery._skills_cache = None  # Force cache rebuild

    generator = SkillGenerator(discovery)

    # Call create_skill without force — should detect skill exists and return correct path
    result_path = generator.create_skill("myskill", force=False)

    assert result_path == global_learned / "myskill", (
        f"Expected learned/myskill/ but got {result_path}. "
        f"Flat-file skill parent is learned/ dir, so we need parent / safe_name."
    )


def test_create_skill_directory_style_returns_parent(tmp_path):
    """BUG-3 (regression guard): For directory-style skills (myskill/SKILL.md),
    create_skill must return myskill/ (i.e. existing.parent)."""
    global_learned = tmp_path / "learned"
    global_learned.mkdir()

    # Create a directory-style skill
    skill_dir = global_learned / "myskill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# My Skill\n\nContent.", encoding="utf-8")

    discovery = SkillDiscovery(skills_dir=tmp_path)
    discovery.global_learned = global_learned
    discovery._skills_cache = None

    generator = SkillGenerator(discovery)
    result_path = generator.create_skill("myskill", force=False)

    assert result_path == skill_dir, f"Expected learned/myskill/ but got {result_path}"


# ---------------------------------------------------------------------------
# BUG-4: Silent skill loss when resolve_skill returns None during reuse
# ---------------------------------------------------------------------------


def test_generate_from_readme_reuse_null_resolve_falls_through(tmp_path):
    """BUG-4: When resolve_skill returns None (stale cache / deleted file) for
    a 'reuse' candidate, the skill must NOT be silently lost — it must be created."""
    global_learned = tmp_path / "learned"
    global_learned.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    target_dir = output_dir / "skills" / "project"

    discovery = SkillDiscovery(skills_dir=tmp_path)
    discovery.global_learned = global_learned
    discovery.project_local_dir = None

    generator = SkillGenerator(discovery)

    # Patch: check_global_skill_reuse returns "reuse" for fastapi-endpoints,
    # but resolve_skill returns None (simulating stale cache / missing file)
    with patch.object(generator, "check_global_skill_reuse", return_value={"fastapi-endpoints": "reuse"}):
        with patch.object(discovery, "resolve_skill", return_value=None):
            generated = generator.generate_from_readme(
                readme_content="# FastAPI Project\n- Uses fastapi",
                tech_stack=["fastapi"],
                output_dir=output_dir,
            )

    # The skill must NOT be silently lost — it should fall through to create
    assert len(generated) > 0, "Skill was silently lost when resolve_skill returned None (BUG-4)"
    assert any("fastapi" in name for name in generated), f"Expected fastapi skill in generated, got: {generated}"


# ---------------------------------------------------------------------------
# BUG-5: CoworkStrategy must not force use_ai=True
# ---------------------------------------------------------------------------


def test_cowork_strategy_does_not_force_use_ai(tmp_path):
    """BUG-5: CoworkStrategy.generate() must call create_skill with use_ai=False."""
    from generator.strategies.cowork_strategy import CoworkStrategy

    strategy = CoworkStrategy()

    captured_kwargs = {}

    def fake_create_skill(skill_name, readme_content, **kwargs):
        captured_kwargs.update(kwargs)
        # Return a valid tuple so the strategy completes
        from generator.skill_creator import SkillMetadata
        from generator.utils.quality_checker import QualityReport

        meta = SkillMetadata(name=skill_name, description="test")
        quality = QualityReport(score=80.0, passed=True)
        return "# Skill content", meta, quality

    with patch("generator.skill_creator.CoworkSkillCreator.create_skill", side_effect=fake_create_skill):
        result = strategy.generate("test-skill", tmp_path, "# README content", "gemini")

    assert "use_ai" in captured_kwargs, "create_skill was not called with use_ai kwarg"
    assert (
        captured_kwargs["use_ai"] is False
    ), f"CoworkStrategy must pass use_ai=False, got: {captured_kwargs['use_ai']}"


# ---------------------------------------------------------------------------
# DESIGN-1: QualityReport should be imported from quality_checker, not duplicated
# ---------------------------------------------------------------------------


def test_quality_report_single_source():
    """DESIGN-1: skill_creator.QualityReport and quality_checker.QualityReport
    must be the SAME class (no duplicate definition)."""
    from generator.utils.quality_checker import QualityReport as CheckerReport
    from generator.skill_creator import QualityReport as CreatorReport

    assert CreatorReport is CheckerReport, (
        "QualityReport is defined in two places — skill_creator.py has its own copy. "
        "DESIGN-1: Remove it from skill_creator.py and import from quality_checker."
    )


# ---------------------------------------------------------------------------
# DESIGN-3: detect_skill_needs() tool_map must cover TECH_SKILL_NAMES
# ---------------------------------------------------------------------------


def test_detect_skill_needs_uses_full_tech_map(tmp_path):
    """DESIGN-3: detect_skill_needs() tool_map should cover the same techs as
    SkillGenerator.TECH_SKILL_NAMES so generate_all() doesn't miss 80% of technologies."""
    creator = CoworkSkillCreator(tmp_path)
    tech_map_keys = set(creator.detect_skill_needs.__func__.__code__.co_consts)
    # Instead of inspecting bytecode, do a functional check:
    # For each key in TECH_SKILL_NAMES, create a temp project with requirements.txt
    # and verify detect_skill_needs() emits at least one skill.

    # Minimum expected techs that detect_skill_needs() should handle
    expected_techs = {"fastapi", "flask", "django", "react", "pytest", "docker"}

    for tech in expected_techs:
        # Write a minimal project with requirements containing the tech
        req = tmp_path / "requirements.txt"
        req.write_text(f"{tech}==1.0\n", encoding="utf-8")
        readme = tmp_path / "README.md"
        readme.write_text(f"# Project\n\n- Uses {tech}", encoding="utf-8")

        skills = creator.detect_skill_needs(tmp_path)
        assert len(skills) > 0, (
            f"detect_skill_needs() returned nothing for tech '{tech}'. "
            f"DESIGN-3: Expand tool_map to cover all entries in TECH_SKILL_NAMES."
        )

        # Cleanup for next iteration
        req.unlink()
        readme.unlink()


# ---------------------------------------------------------------------------
# DESIGN-4: Cache must be invalidated after creating a new skill
# ---------------------------------------------------------------------------


def test_cache_invalidated_after_invalidate_call(tmp_path):
    """DESIGN-4: SkillDiscovery.invalidate_cache() must clear _skills_cache so
    the next lookup rebuilds from disk."""
    discovery = SkillDiscovery(skills_dir=tmp_path)
    discovery.global_learned = tmp_path / "learned"
    discovery.global_learned.mkdir(exist_ok=True)

    # Prime the cache (empty)
    _ = discovery.list_skills()
    assert discovery._skills_cache is not None, "Cache should be built after list_skills()"

    # Write a new skill AFTER cache was built
    new_skill = discovery.global_learned / "new-skill.md"
    new_skill.write_text("# New Skill\n\n## Purpose\nTest.", encoding="utf-8")

    # Without invalidation the cache won't see the new skill
    cached_before = discovery.list_skills()

    # Invalidate and re-query
    discovery.invalidate_cache()
    assert discovery._skills_cache is None, "invalidate_cache() must set _skills_cache to None"

    fresh_skills = discovery.list_skills()
    assert (
        "new-skill" in fresh_skills
    ), f"After invalidate_cache(), new skill must appear in list_skills(). Got: {list(fresh_skills.keys())}"

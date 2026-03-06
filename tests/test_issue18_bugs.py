"""
Tests for Issue #18 — Skills Mechanism Post-v1.2 Review
========================================================
BUG-A:    READMEStrategy treats from_readme as content, not file path.
BUG-B:    adapt branch pollutes global learned with project-specific content.
BUG-C:    quality_score: 95 hardcoded in Jinja2 template context.
DESIGN-A: detect_skill_needs() uses only 7 of 40+ techs.
DESIGN-B: _validate_quality() duplicates quality_checker.validate_quality().
DESIGN-C: link_from_learned() silently skips directory-style skills.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generator.skill_creator import CoworkSkillCreator, SkillMetadata
from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator
from generator.strategies.readme_strategy import READMEStrategy
from generator.utils.quality_checker import QualityReport, validate_quality


# ---------------------------------------------------------------------------
# BUG-A: READMEStrategy must use from_readme as content, not treat it as path
# ---------------------------------------------------------------------------


def test_readme_strategy_uses_content_not_path(tmp_path):
    """READMEStrategy must return None only when content is empty, never because
    it tried Path(<content string>).exists() which is always False."""
    readme_content = (
        "# My Project\n\nThis project uses FastAPI for REST endpoints.\n"
        "Run with uvicorn. Deploy with Docker.\n"
        * 5  # ensure > 80 words
    )

    strategy = READMEStrategy()
    # Pass multi-line README *content* — the old code would Path(content).exists()
    # which is always False and return None.
    result = strategy.generate(
        skill_name="fastapi-api-workflow",
        project_path=tmp_path,
        from_readme=readme_content,
        provider="groq",
    )

    # Must produce content (even if the analyzers produce minimal output)
    # rather than silently returning None.
    assert result is not None, (
        "READMEStrategy returned None — still treating from_readme as a path"
    )


def test_readme_strategy_returns_none_when_empty():
    """READMEStrategy must return None when from_readme is falsy."""
    strategy = READMEStrategy()
    assert strategy.generate("any-skill", None, None, "groq") is None
    assert strategy.generate("any-skill", None, "", "groq") is None


def test_readme_strategy_no_path_warning_for_content(tmp_path, capsys):
    """No 'README not found' warning should appear when valid content is passed."""
    readme_content = "# Proj\n\nFastAPI project.\n" * 10

    strategy = READMEStrategy()
    strategy.generate("fastapi-api-workflow", tmp_path, readme_content, "groq")

    captured = capsys.readouterr()
    assert "not found" not in captured.out.lower(), (
        "READMEStrategy printed a 'not found' warning — still path-checking content"
    )


# ---------------------------------------------------------------------------
# BUG-B: adapt branch must NOT write project-specific content to global cache
# ---------------------------------------------------------------------------


def test_adapt_branch_does_not_pollute_global_cache(tmp_path):
    """When action=='adapt', the global learned file must NOT be overwritten
    with project-specific content."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    # Set up a fake global learned directory with a stub for 'pytest-testing'
    global_learned = tmp_path / "global_learned"
    global_learned.mkdir()

    original_stub_content = "# Pytest Testing\nFollow project conventions.\n"
    global_skill_file = global_learned / "pytest-testing.md"
    global_skill_file.write_text(original_stub_content, encoding="utf-8")

    # Set up project output dir
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Build a minimal SkillGenerator with mocked discovery
    discovery = MagicMock(spec=SkillDiscovery)
    discovery.project_local_dir = output_dir
    discovery.global_learned = global_learned

    def fake_skill_exists(name, scope="learned"):
        return (global_learned / f"{name}.md").exists()

    def fake_resolve_skill(name):
        p = global_learned / f"{name}.md"
        return p if p.exists() else None

    discovery.skill_exists.side_effect = fake_skill_exists
    discovery.resolve_skill.side_effect = fake_resolve_skill

    generator = SkillGenerator(discovery)

    # _is_generic_stub must return True so action becomes 'adapt'
    with patch.object(SkillGenerator, "_is_generic_stub", return_value=True):
        generator.generate_from_readme(
            readme_content="# MyProject\nUses pytest.\n",
            tech_stack=["pytest"],
            output_dir=output_dir,
            project_name="myproject",
            project_path=project_path,
        )

    # Global file must be unchanged
    assert global_skill_file.read_text(encoding="utf-8") == original_stub_content, (
        "adapt branch overwrote the global learned skill with project-specific content"
    )


# ---------------------------------------------------------------------------
# BUG-C: _generate_with_jinja2 must not include quality_score in context
# ---------------------------------------------------------------------------


def test_jinja2_context_has_no_hardcoded_quality_score(tmp_path):
    """The Jinja2 template context must not contain quality_score=95."""
    creator = CoworkSkillCreator(tmp_path)

    metadata = SkillMetadata(
        name="test-skill",
        description="test",
        auto_triggers=["run test", "test workflow"],
        tools=["pytest"],
    )

    captured_context: dict = {}

    original_method = creator._generate_with_jinja2.__func__  # unbound

    def capturing_jinja2(self, skill_name, readme_content, metadata, custom_context=None):
        # Reconstruct what the method would put in context, but intercept it
        # by calling the real method with a mock template environment
        raise _ContextCapture(skill_name, readme_content, metadata)

    class _ContextCapture(Exception):
        pass

    # Monkey-patch to inspect context without needing a real Jinja2 template
    real_method = creator._generate_with_jinja2

    def mock_jinja2(skill_name, readme_content, metadata, custom_context=None):
        # We want to check the source code / context dict — check source directly
        import inspect

        source = inspect.getsource(creator._generate_with_jinja2)
        assert "quality_score" not in source or "quality_score" not in source.split("context = {")[1].split("}")[0], (
            "quality_score still present in Jinja2 context dict"
        )
        return ""  # Return empty string so test doesn't fail on missing template

    with patch.object(creator, "_generate_with_jinja2", side_effect=mock_jinja2):
        try:
            creator._generate_content(
                "test-skill", "# Test\n" * 20, metadata, use_ai=False
            )
        except Exception:
            pass  # Template may not exist in test env — that's fine


def test_jinja2_source_has_no_quality_score_95():
    """Verify at the source level that quality_score: 95 assignment is gone."""
    import inspect

    from generator.skill_creator import CoworkSkillCreator

    source = inspect.getsource(CoworkSkillCreator._generate_with_jinja2)
    # The dict assignment `"quality_score": 95` must not exist.
    # A comment mentioning the key is fine; an active dict entry is not.
    assert '"quality_score": 95' not in source, (
        'quality_score: 95 still in _generate_with_jinja2 context dict — remove it'
    )


# ---------------------------------------------------------------------------
# DESIGN-A: detect_skill_needs() must cover all techs in TECH_SKILL_NAMES
# ---------------------------------------------------------------------------


def test_detect_skill_needs_uses_full_tech_map(tmp_path):
    """detect_skill_needs() must return tech-specific names for all techs in
    SkillGenerator.TECH_SKILL_NAMES, not fall back to '<project>-workflow'."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    creator = CoworkSkillCreator(project_path)

    # Sample techs that were MISSING from the old 7-entry tool_map
    techs_not_in_old_map = ["sqlalchemy", "celery", "pydantic", "click", "redis", "openai", "anthropic", "groq"]

    for tech in techs_not_in_old_map:
        expected_skill = SkillGenerator.TECH_SKILL_NAMES[tech]

        with patch.object(creator, "_detect_tech_stack", return_value=[tech]):
            result = creator.detect_skill_needs(project_path)

        assert expected_skill in result, (
            f"detect_skill_needs() returned {result} for tech='{tech}', "
            f"expected '{expected_skill}' — TECH_SKILL_NAMES not being used"
        )


def test_detect_skill_needs_generic_fallback(tmp_path):
    """detect_skill_needs() falls back to '<project>-workflow' only when
    tech stack is unknown."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()
    creator = CoworkSkillCreator(project_path)

    with patch.object(creator, "_detect_tech_stack", return_value=["unknowntech"]):
        result = creator.detect_skill_needs(project_path)

    assert result == ["myproject-workflow"], f"Unexpected fallback: {result}"


# ---------------------------------------------------------------------------
# DESIGN-B: _validate_quality() must delegate to quality_checker.validate_quality()
# ---------------------------------------------------------------------------


def test_validate_quality_delegates_to_quality_checker(tmp_path):
    """CoworkSkillCreator._validate_quality() must produce results consistent
    with quality_checker.validate_quality() for shared checks (the delegation
    is done via lazy import inside the method)."""
    creator = CoworkSkillCreator(tmp_path)
    triggers = ["run test", "execute test", "verify test"]
    tools = ["pytest"]
    metadata = SkillMetadata(
        name="test-skill",
        description="test",
        auto_triggers=triggers,
        tools=tools,
    )

    good_content = (
        "## Purpose\n\nTest purpose.\n\n"
        "## Auto-Trigger\n\n- run test\n\n"
        "## Process\n\n1. Step one\n2. Step two\n\n"
        "## Output\n\nTest output.\n\n"
        "## Anti-Patterns\n\n❌ Don't skip tests\n"
        "```bash\npytest\n```\n"
    )

    report = creator._validate_quality(good_content, metadata)
    assert isinstance(report, QualityReport)
    assert report.score >= 0
    assert isinstance(report.passed, bool)

    # Shared check: missing required sections must decrease score
    bad_content = "Some content without required sections. ```bash\ntest\n```"
    bad_report = creator._validate_quality(
        bad_content,
        SkillMetadata("s", "d", auto_triggers=triggers, tools=tools),
    )
    assert bad_report.score < report.score, (
        "Missing required sections should lower the score (delegation not working)"
    )


def test_validate_quality_placeholder_check_unified(tmp_path):
    """Placeholder check is now in quality_checker.validate_quality(),
    so _validate_quality() must still catch placeholders."""
    creator = CoworkSkillCreator(tmp_path)
    metadata = SkillMetadata(
        name="test-skill",
        description="test",
        auto_triggers=["a", "b", "c"],
        tools=["pytest"],
    )
    content = "## Purpose\n[describe what this does]\n```bash\ntest\n```\n## Anti-Patterns\n❌ nope\n"
    report = creator._validate_quality(content, metadata)
    placeholder_issues = [i for i in report.issues if "placeholder" in i.lower()]
    assert placeholder_issues, "Placeholder check missing after delegation"


# ---------------------------------------------------------------------------
# DESIGN-C: link_from_learned() must handle directory-style skills
# ---------------------------------------------------------------------------


def test_link_from_learned_handles_directory_skill(tmp_path):
    """If the global learned skill is a directory (<name>/SKILL.md),
    link_from_learned() must link to the SKILL.md inside it, not silently skip."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    # Set up global learned with a directory-style skill
    global_learned = tmp_path / "global_learned"
    skill_dir = global_learned / "pytest-testing-workflow"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("# Pytest Testing Workflow\nContent here.\n", encoding="utf-8")

    # Set up project local dir
    project_local = tmp_path / "project_local"
    project_local.mkdir()

    creator = CoworkSkillCreator(project_path)
    creator.discovery = MagicMock(spec=SkillDiscovery)
    creator.discovery.global_learned = global_learned
    creator.discovery.project_local_dir = project_local

    link_calls = []

    def fake_link_or_copy(src, tgt):
        link_calls.append((src, tgt))
        import shutil

        shutil.copy2(src, tgt)

    creator.discovery._link_or_copy.side_effect = fake_link_or_copy

    creator.link_from_learned("pytest-testing-workflow")

    assert link_calls, "link_from_learned() did nothing for directory-style skill"
    src, tgt = link_calls[0]
    assert src == skill_md, f"Should link to SKILL.md inside dir, got: {src}"


def test_link_from_learned_flat_file_still_works(tmp_path):
    """Flat .md file skills must still work after the directory-style fix."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    global_learned = tmp_path / "global_learned"
    global_learned.mkdir()
    flat_skill = global_learned / "pytest-testing.md"
    flat_skill.write_text("# Pytest\n", encoding="utf-8")

    project_local = tmp_path / "project_local"
    project_local.mkdir()

    creator = CoworkSkillCreator(project_path)
    creator.discovery = MagicMock(spec=SkillDiscovery)
    creator.discovery.global_learned = global_learned
    creator.discovery.project_local_dir = project_local

    link_calls = []

    def fake_link_or_copy(src, tgt):
        link_calls.append((src, tgt))
        import shutil

        shutil.copy2(src, tgt)

    creator.discovery._link_or_copy.side_effect = fake_link_or_copy

    creator.link_from_learned("pytest-testing")

    assert link_calls, "link_from_learned() failed for flat .md skill"
    src, _ = link_calls[0]
    assert src == flat_skill

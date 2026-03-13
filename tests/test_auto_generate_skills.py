"""Tests for CoworkSkillCreator.auto_generate_skills() — BUG-1 regression guard.

BUG-1: auto_generate_skills() previously had its own hardcoded tech→skill map
that diverged from SkillGenerator.TECH_SKILL_NAMES.  It produced wrong names
like "fastapi-api-workflow" instead of "fastapi-endpoints" and
"pytest-testing-workflow" instead of "pytest-testing".
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from generator.skill_creator import CoworkSkillCreator
from generator.skill_generator import SkillGenerator


class TestAutoGenerateSkillsNames:
    """Verify that auto_generate_skills() uses TECH_SKILL_NAMES as the sole source of truth."""

    def _make_readme(self, *techs: str) -> str:
        items = "\n".join(f"- {t}" for t in techs)
        return f"# My Project\n\n## Tech Stack\n{items}\n"

    def _run(self, tmp_path: Path, readme: str):
        """Run auto_generate_skills and return the list of generated file names (stems)."""
        creator = CoworkSkillCreator(tmp_path)
        output_dir = tmp_path / "skills"
        output_dir.mkdir()

        # Patch create_skill so we don't need a real project on disk.
        # We only care about the *names* that auto_generate_skills computes.
        captured_names: list = []

        def fake_create_skill(skill_name, readme_content, **kwargs):
            captured_names.append(skill_name)
            from generator.utils.quality_checker import QualityReport
            from generator.skill_creator import SkillMetadata

            meta = SkillMetadata(name=skill_name, description="stub")
            quality = QualityReport(score=90.0, passed=True, issues=[], warnings=[], suggestions=[])
            return f"# {skill_name}\n", meta, quality

        with patch.object(creator, "create_skill", side_effect=fake_create_skill):
            with patch.object(creator, "_detect_tech_stack", return_value=list(
                {t for t in readme.lower().split() if t in SkillGenerator.TECH_SKILL_NAMES}
            )):
                creator.auto_generate_skills(readme, output_dir)

        return captured_names

    def test_fastapi_uses_canonical_name(self, tmp_path):
        """fastapi should produce 'fastapi-endpoints', NOT 'fastapi-api-workflow'."""
        creator = CoworkSkillCreator(tmp_path)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        captured: list = []

        def fake_create(name, readme, **kwargs):
            captured.append(name)
            from generator.utils.quality_checker import QualityReport
            from generator.skill_creator import SkillMetadata

            meta = SkillMetadata(name=name, description="stub")
            q = QualityReport(score=90.0, passed=True, issues=[], warnings=[], suggestions=[])
            return f"# {name}\n", meta, q

        with patch.object(creator, "create_skill", side_effect=fake_create):
            with patch.object(creator, "_detect_tech_stack", return_value=["fastapi"]):
                creator.auto_generate_skills("# readme\n- fastapi", output_dir)

        assert "fastapi-endpoints" in captured, f"Expected 'fastapi-endpoints', got {captured}"
        assert not any("api-workflow" in n for n in captured), (
            f"Old broken name 'fastapi-api-workflow' must not appear. Got: {captured}"
        )

    def test_pytest_uses_canonical_name(self, tmp_path):
        """pytest should produce 'pytest-testing', NOT 'pytest-testing-workflow'."""
        creator = CoworkSkillCreator(tmp_path)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        captured: list = []

        def fake_create(name, readme, **kwargs):
            captured.append(name)
            from generator.utils.quality_checker import QualityReport
            from generator.skill_creator import SkillMetadata

            meta = SkillMetadata(name=name, description="stub")
            q = QualityReport(score=90.0, passed=True, issues=[], warnings=[], suggestions=[])
            return f"# {name}\n", meta, q

        with patch.object(creator, "create_skill", side_effect=fake_create):
            with patch.object(creator, "_detect_tech_stack", return_value=["pytest"]):
                creator.auto_generate_skills("# readme\n- pytest", output_dir)

        assert "pytest-testing" in captured, f"Expected 'pytest-testing', got {captured}"
        assert not any(n == "pytest-testing-workflow" for n in captured), (
            f"Old broken name 'pytest-testing-workflow' must not appear. Got: {captured}"
        )

    def test_unknown_tech_falls_back_to_project_workflow(self, tmp_path):
        """Unknown tech that has no TECH_SKILL_NAMES entry should yield a project workflow."""
        creator = CoworkSkillCreator(tmp_path)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        captured: list = []

        def fake_create(name, readme, **kwargs):
            captured.append(name)
            from generator.utils.quality_checker import QualityReport
            from generator.skill_creator import SkillMetadata

            meta = SkillMetadata(name=name, description="stub")
            q = QualityReport(score=90.0, passed=True, issues=[], warnings=[], suggestions=[])
            return f"# {name}\n", meta, q

        # "cobol" is not in TECH_SKILL_NAMES
        with patch.object(creator, "create_skill", side_effect=fake_create):
            with patch.object(creator, "_detect_tech_stack", return_value=["cobol"]):
                creator.auto_generate_skills("# readme\n- cobol", output_dir)

        assert any(n.endswith("-workflow") for n in captured), (
            f"Expected a generic *-workflow fallback, got {captured}"
        )

    def test_all_generated_names_match_tech_skill_names(self, tmp_path):
        """Every skill name produced must be a value from TECH_SKILL_NAMES (or the fallback)."""
        creator = CoworkSkillCreator(tmp_path)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        captured: list = []

        def fake_create(name, readme, **kwargs):
            captured.append(name)
            from generator.utils.quality_checker import QualityReport
            from generator.skill_creator import SkillMetadata

            meta = SkillMetadata(name=name, description="stub")
            q = QualityReport(score=90.0, passed=True, issues=[], warnings=[], suggestions=[])
            return f"# {name}\n", meta, q

        techs = ["fastapi", "pytest", "docker", "react", "flask", "django", "redis", "postgresql"]
        with patch.object(creator, "create_skill", side_effect=fake_create):
            with patch.object(creator, "_detect_tech_stack", return_value=techs):
                creator.auto_generate_skills("# readme", output_dir)

        valid_values = set(SkillGenerator.TECH_SKILL_NAMES.values())
        for name in captured:
            assert name in valid_values or name.endswith("-workflow"), (
                f"Unexpected skill name '{name}' not in TECH_SKILL_NAMES values and not a fallback."
            )

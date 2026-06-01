"""Tests for generator.skills.skill_selection.

Covers the hybrid selection rule: curated profiles win, unmapped-but-skill-worthy
techs get a synthesized "{tech}-workflow", and languages / generic infrastructure /
unknown techs produce no skill.
"""

from __future__ import annotations

import pytest

from generator.skills.skill_selection import NON_SKILL_TECHS, is_skill_worthy, select_skill_names

# ---------------------------------------------------------------------------
# is_skill_worthy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tech", ["whisper", "rich", "mysql", "jinja2"])
def test_unmapped_library_categories_are_skill_worthy(tech):
    """Unmapped techs in backend/database categories deserve a synthesized skill."""
    assert is_skill_worthy(tech) is True


@pytest.mark.parametrize("tech", ["git", "linux", "yaml", "kubernetes"])
def test_generic_infrastructure_is_not_skill_worthy(tech):
    """Generic infrastructure techs must not produce a synthesized skill."""
    assert is_skill_worthy(tech) is False


@pytest.mark.parametrize("tech", ["python", "go", "javascript", "rust", "typescript"])
def test_languages_are_not_skill_worthy(tech):
    """Languages never get their own skill."""
    assert is_skill_worthy(tech) is False


@pytest.mark.parametrize("tech", ["numpy", "pandas", "totally-unknown-lib"])
def test_unknown_techs_are_not_skill_worthy(tech):
    """A tech with no profile/category never reaches synthesis (no noise)."""
    assert is_skill_worthy(tech) is False


def test_denylist_overrides_skill_worthy_category():
    """asyncio is backend but explicitly denied (stdlib, too ubiquitous)."""
    assert "asyncio" in NON_SKILL_TECHS
    assert is_skill_worthy("asyncio") is False


def test_is_skill_worthy_is_case_insensitive():
    assert is_skill_worthy("Whisper") is True
    assert is_skill_worthy("GIT") is False


# ---------------------------------------------------------------------------
# select_skill_names
# ---------------------------------------------------------------------------


def test_curated_mapping_wins():
    """Mapped techs use their curated skill name, not a synthesized one."""
    names = select_skill_names(["pytest", "groq", "docker"], "proj")
    assert "pytest-testing" in names
    assert "groq-api" in names
    assert "docker-deployment" in names
    assert "pytest-workflow" not in names


def test_unmapped_skill_worthy_tech_is_synthesized():
    """Whisper has no curated skill_name → synthesized whisper-workflow."""
    names = select_skill_names(["whisper", "rich"], "proj")
    assert "whisper-workflow" in names
    assert "rich-workflow" in names


def test_mixed_stack_combines_curated_and_synthesized():
    names = select_skill_names(["pydantic", "whisper", "git", "python"], "v-shell")
    assert "pydantic-validation" in names  # curated
    assert "whisper-workflow" in names  # synthesized
    assert "git-workflow" not in names  # generic infra, skipped
    assert "python-workflow" not in names  # language, skipped


def test_empty_stack_falls_back_to_project_workflow():
    assert select_skill_names([], "myproj") == ["myproj-workflow"]


def test_language_only_stack_falls_back_to_project_workflow():
    assert select_skill_names(["python", "go"], "myproj") == ["myproj-workflow"]


def test_result_is_deduplicated_and_sorted():
    names = select_skill_names(["pytest", "pytest", "groq"], "proj")
    assert names == sorted(names)
    assert len(names) == len(set(names))

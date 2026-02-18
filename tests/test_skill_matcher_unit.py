"""
Tests for SkillMatcher-equivalent functionality.
SkillMatcher was removed in v1.1 cleanup.
Equivalent functionality is now in SkillDiscovery.
"""

import pytest
from pathlib import Path

from generator.skill_discovery import SkillDiscovery


@pytest.fixture
def mock_dirs(tmp_path):
    learned = tmp_path / "learned"
    builtin = tmp_path / "builtin"
    learned.mkdir()
    builtin.mkdir()
    return tmp_path, learned, builtin


def test_find_learned_skill(mock_dirs):
    """SkillDiscovery should find skills in the learned directory."""
    project_root, learned, builtin = mock_dirs

    # Create learned skill directory with SKILL.md
    skill_dir = learned / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill: My Skill\n\nlearned content")

    discovery = SkillDiscovery.__new__(SkillDiscovery)
    discovery.global_learned = learned
    discovery.global_builtin = builtin
    discovery.project_path = None
    discovery.project_skills_root = None
    discovery.project_local_dir = None
    discovery.project_builtin_link = None
    discovery.project_learned_link = None
    discovery.global_root = project_root

    result = discovery.resolve_skill("my-skill")
    assert result is not None
    assert "learned content" in result.read_text()


def test_find_builtin_skill(mock_dirs):
    """SkillDiscovery should find skills in the builtin directory."""
    project_root, learned, builtin = mock_dirs

    skill_dir = builtin / "std-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill: Std Skill\n\nbuiltin content")

    discovery = SkillDiscovery.__new__(SkillDiscovery)
    discovery.global_learned = learned
    discovery.global_builtin = builtin
    discovery.project_path = None
    discovery.project_skills_root = None
    discovery.project_local_dir = None
    discovery.project_builtin_link = None
    discovery.project_learned_link = None
    discovery.global_root = project_root

    result = discovery.resolve_skill("std-skill")
    assert result is not None
    assert "builtin content" in result.read_text()


def test_priority_learned_over_builtin(mock_dirs):
    """Learned skills should take priority over builtin."""
    project_root, learned, builtin = mock_dirs

    # Create both
    for d, label in [(learned, "learned version"), (builtin, "builtin version")]:
        skill_dir = d / "conflict"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# Skill: Conflict\n\n{label}")

    discovery = SkillDiscovery.__new__(SkillDiscovery)
    discovery.global_learned = learned
    discovery.global_builtin = builtin
    discovery.project_path = None
    discovery.project_skills_root = None
    discovery.project_local_dir = None
    discovery.project_builtin_link = None
    discovery.project_learned_link = None
    discovery.global_root = project_root

    result = discovery.resolve_skill("conflict")
    assert result is not None
    assert "learned version" in result.read_text()


def test_missing_skill_returns_none(mock_dirs):
    """resolve_skill should return None for unknown skills."""
    project_root, learned, builtin = mock_dirs

    discovery = SkillDiscovery.__new__(SkillDiscovery)
    discovery.global_learned = learned
    discovery.global_builtin = builtin
    discovery.project_path = None
    discovery.project_skills_root = None
    discovery.project_local_dir = None
    discovery.project_builtin_link = None
    discovery.project_learned_link = None
    discovery.global_root = project_root

    result = discovery.resolve_skill("nonexistent-skill")
    assert result is None

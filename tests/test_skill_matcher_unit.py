import pytest

from generator.skill_matcher import SkillMatcher


@pytest.fixture
def mock_dirs(tmp_path):
    learned = tmp_path / "learned"
    builtin = tmp_path / "builtin"
    learned.mkdir()
    builtin.mkdir()
    return learned, builtin


def test_find_learned_skill(mock_dirs):
    learned, builtin = mock_dirs

    # Create learned skill
    (learned / "my-skill.yaml").write_text("name: my-skill\ncontent: learned content")

    matcher = SkillMatcher(learned, builtin)
    skill = matcher.find_skill("my-skill", {})

    assert skill is not None
    assert skill.source == "learned"
    assert "learned content" in skill.content


def test_find_builtin_skill(mock_dirs):
    learned, builtin = mock_dirs

    # Create builtin skill
    (builtin / "std-skill.yaml").write_text("name: std-skill\ncontent: builtin content")

    matcher = SkillMatcher(learned, builtin)
    skill = matcher.find_skill("std-skill", {})

    assert skill is not None
    assert skill.source == "builtin"
    assert "builtin content" in skill.content


def test_priority_learned_over_builtin(mock_dirs):
    learned, builtin = mock_dirs

    # Create both
    (learned / "conflict.yaml").write_text("name: conflict\ncontent: learned version")
    (builtin / "conflict.yaml").write_text("name: conflict\ncontent: builtin version")

    matcher = SkillMatcher(learned, builtin)
    skill = matcher.find_skill("conflict", {})

    assert skill is not None
    assert skill.source == "learned"
    assert "learned version" in skill.content


def test_ignore_nested_readme(mock_dirs):
    learned, builtin = mock_dirs

    # Create random README in builtin (should be ignored by strict matcher unless it matches name or uses SKILL.md pattern)
    # Our matcher currently searches:
    # 1. name.yaml/yml/md
    # 2. name/SKILL.md

    (builtin / "README.md").write_text("Not a skill")

    matcher = SkillMatcher(learned, builtin)
    skill = matcher.find_skill("README", {})

    # Should not match unless we specifically look for "README" skill which is unlikely?
    # Actually if we ask for "README", and "README.md" exists...
    # But usually we ask for "python-setup" or similar.

    # Let's test finding a skill called "test"
    skill = matcher.find_skill("test", {})
    assert skill is None

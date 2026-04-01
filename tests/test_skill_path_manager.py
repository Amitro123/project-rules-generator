"""Unit tests for SkillPathManager.save_learned_skill and get_skill_path."""

import pytest

from generator.storage.skill_paths import SkillPathManager


@pytest.fixture()
def spm(tmp_path, monkeypatch):
    """SkillPathManager with all global paths redirected to tmp_path."""
    global_dir = tmp_path / ".project-rules-generator"
    monkeypatch.setattr(SkillPathManager, "GLOBAL_DIR", global_dir)
    monkeypatch.setattr(SkillPathManager, "GLOBAL_BUILTIN", global_dir / "builtin")
    monkeypatch.setattr(SkillPathManager, "GLOBAL_LEARNED", global_dir / "learned")
    # Skip real builtin sync (no source dir in tmp)
    monkeypatch.setattr(SkillPathManager, "BUILTIN_SOURCE", tmp_path / "no-source")
    return SkillPathManager


# ---------------------------------------------------------------------------
# save_learned_skill
# ---------------------------------------------------------------------------


def test_save_learned_skill_creates_subfolder_layout(spm):
    """Skill saved as {category}/{name}/SKILL.md."""
    path = spm.save_learned_skill(
        {"name": "async-patterns", "content": "# Async Patterns\nDO: use asyncio"},
        category="fastapi",
    )
    assert path.name == "SKILL.md"
    assert path.parent.name == "async-patterns"
    assert path.parent.parent.name == "fastapi"
    assert path.read_text(encoding="utf-8") == "# Async Patterns\nDO: use asyncio"


def test_save_learned_skill_missing_name_falls_back(spm):
    """Skill dict without 'name' key uses 'unnamed-skill'."""
    path = spm.save_learned_skill({"content": "some content"}, category="misc")
    assert path.parent.name == "unnamed-skill"


def test_save_learned_skill_empty_content(spm):
    """Skill with empty content writes an empty file without error."""
    path = spm.save_learned_skill({"name": "empty-skill", "content": ""}, category="misc")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_save_learned_skill_overwrites_on_second_call(spm):
    """Calling save_learned_skill twice with updated content overwrites."""
    skill = {"name": "my-skill", "content": "v1"}
    spm.save_learned_skill(skill, category="cat")
    skill["content"] = "v2"
    path = spm.save_learned_skill(skill, category="cat")
    assert path.read_text(encoding="utf-8") == "v2"


def test_save_learned_skill_creates_directories(spm):
    """Ensure the full category/name directory tree is created."""
    spm.save_learned_skill({"name": "deep-skill", "content": "x"}, category="new-cat")
    assert (spm.GLOBAL_LEARNED / "new-cat" / "deep-skill").is_dir()


# ---------------------------------------------------------------------------
# get_skill_path — builtin
# ---------------------------------------------------------------------------


def test_get_skill_path_builtin_subfolder(spm):
    """Resolves builtin/code-review via subfolder layout (name/SKILL.md)."""
    skill_dir = spm.GLOBAL_BUILTIN / "code-review"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Code Review")

    result = spm.get_skill_path("builtin/code-review")
    assert result == skill_file


def test_get_skill_path_builtin_flat_fallback(spm):
    """Falls back to flat .md file when subfolder layout absent."""
    spm.GLOBAL_BUILTIN.mkdir(parents=True)
    flat = spm.GLOBAL_BUILTIN / "tdd.md"
    flat.write_text("# TDD")

    result = spm.get_skill_path("builtin/tdd")
    assert result == flat


def test_get_skill_path_builtin_prefers_subfolder_over_flat(spm):
    """Subfolder layout takes priority over flat file for the same name."""
    spm.GLOBAL_BUILTIN.mkdir(parents=True)
    flat = spm.GLOBAL_BUILTIN / "tdd.md"
    flat.write_text("flat")
    skill_dir = spm.GLOBAL_BUILTIN / "tdd"
    skill_dir.mkdir()
    subfolder = skill_dir / "SKILL.md"
    subfolder.write_text("subfolder")

    result = spm.get_skill_path("builtin/tdd")
    assert result == subfolder


# ---------------------------------------------------------------------------
# get_skill_path — learned
# ---------------------------------------------------------------------------


def test_get_skill_path_learned_with_category(spm):
    """Resolves learned/fastapi/async-patterns to its .md file."""
    cat_dir = spm.GLOBAL_LEARNED / "fastapi"
    cat_dir.mkdir(parents=True)
    skill_file = cat_dir / "async-patterns.md"
    skill_file.write_text("# Async")

    result = spm.get_skill_path("learned/fastapi/async-patterns")
    assert result == skill_file


def test_get_skill_path_learned_without_category_searches_all(spm):
    """Two-part ref (learned/name) searches all category dirs."""
    cat_dir = spm.GLOBAL_LEARNED / "misc"
    cat_dir.mkdir(parents=True)
    skill_file = cat_dir / "my-skill.md"
    skill_file.write_text("# My Skill")

    result = spm.get_skill_path("learned/my-skill")
    assert result == skill_file


def test_get_skill_path_returns_none_when_missing(spm):
    """Returns None for a ref that doesn't exist on disk."""
    spm.GLOBAL_BUILTIN.mkdir(parents=True)
    assert spm.get_skill_path("builtin/nonexistent") is None


def test_get_skill_path_returns_none_for_short_ref(spm):
    """Single-segment ref returns None (ambiguous)."""
    assert spm.get_skill_path("just-a-name") is None


def test_get_skill_path_yaml_extension_supported(spm):
    """Also resolves .yaml extension for builtin skills."""
    spm.GLOBAL_BUILTIN.mkdir(parents=True)
    yaml_file = spm.GLOBAL_BUILTIN / "some-skill.yaml"
    yaml_file.write_text("name: some-skill")

    result = spm.get_skill_path("builtin/some-skill")
    assert result == yaml_file

from pathlib import Path

import pytest

from generator.skills_manager import SkillsManager


@pytest.fixture
def mock_global_home(tmp_path, monkeypatch):
    """Mock the global home directory."""
    from generator.storage.skill_paths import SkillPathManager

    global_home = tmp_path / "global_home"
    monkeypatch.setattr(Path, "home", lambda: global_home)

    # SkillPathManager class attributes are evaluated at import time, so Path.home()
    # monkeypatching alone won't redirect them. Patch the class attributes explicitly.
    global_dir = global_home / ".project-rules-generator"
    monkeypatch.setattr(SkillPathManager, "GLOBAL_DIR", global_dir)
    monkeypatch.setattr(SkillPathManager, "GLOBAL_BUILTIN", global_dir / "builtin")
    monkeypatch.setattr(SkillPathManager, "GLOBAL_LEARNED", global_dir / "learned")

    return global_home


@pytest.fixture
def manager(tmp_path, mock_global_home):
    """Return a SkillsManager instance with a temporary project path."""
    project_path = tmp_path / "project"
    project_path.mkdir()
    return SkillsManager(project_path=project_path)


def test_global_structure_creation(manager):
    """Verify global directories are created."""
    manager.ensure_global_structure()
    assert manager.global_builtin.exists()
    assert manager.global_learned.exists()
    assert manager.global_root.exists()


def test_project_structure_setup(manager):
    """Verify project structure and symlinks/copies."""
    manager.setup_project_structure()

    assert manager.project_local_dir.exists()
    assert manager.project_builtin_link.exists()
    assert manager.project_learned_link.exists()

    # Verify they point to or contain global content
    # Since we can't easily check symlinks in a cross-platform way efficiently here,
    # we just check existence. The implementation falls back to copy if symlink fails.


def test_priority_resolution(manager):
    """Verify priority: Project > Learned > Builtin."""
    skill_name = "conflict-skill"

    # Setup paths
    manager.ensure_global_structure()
    manager.setup_project_structure()

    builtin_skill = manager.global_builtin / f"{skill_name}.md"
    learned_skill = manager.global_learned / f"{skill_name}.md"
    project_skill = manager.project_local_dir / f"{skill_name}.md"

    # 1. Builtin only
    builtin_skill.write_text("BUILTIN", encoding="utf-8")
    manager.discovery._skills_cache = None  # Invalidate cache after filesystem change
    assert manager.resolve_skill(skill_name).read_text(encoding="utf-8") == "BUILTIN"

    # 2. Learned overrides Builtin
    learned_skill.write_text("LEARNED", encoding="utf-8")
    manager.discovery._skills_cache = None  # Invalidate cache after filesystem change
    assert manager.resolve_skill(skill_name).read_text(encoding="utf-8") == "LEARNED"

    # 3. Project overrides Learned
    project_skill.write_text("PROJECT", encoding="utf-8")
    manager.discovery._skills_cache = None  # Invalidate cache after filesystem change
    assert manager.resolve_skill(skill_name).read_text(encoding="utf-8") == "PROJECT"


def test_create_skill_global(manager):
    """Verify create_skill writes to global_learned by default (scope='learned').

    create_skill() routes to global_learned for reusable skills by default.
    Use scope='project' to write to project_local_dir instead.
    """
    skill_name = "new-global-skill"
    manager.ensure_global_structure()
    manager.setup_project_structure()
    manager.create_skill(skill_name)

    # create_skill() writes to global_learned by default
    expected_path = manager.global_learned / skill_name / "SKILL.md"
    assert expected_path.exists()
    assert "Skill: New Global Skill" in expected_path.read_text(encoding="utf-8")


def test_create_skill_project_scope(manager):
    """Verify create_skill with scope='project' writes to project_local_dir."""
    skill_name = "project-skill"
    manager.ensure_global_structure()
    manager.setup_project_structure()
    manager.create_skill(skill_name, scope="project")

    expected_path = manager.project_local_dir / skill_name / "SKILL.md"
    assert expected_path.exists(), (
        f"Skill should be in project_local_dir when scope='project'. " f"project_local_dir={manager.project_local_dir}"
    )


def test_create_skill_fallback_to_global_learned_when_no_project_setup(manager):
    """create_skill defaults to global_learned regardless of project setup state."""
    skill_name = "fallback-skill"
    manager.ensure_global_structure()
    manager.create_skill(skill_name)

    expected_path = manager.global_learned / skill_name / "SKILL.md"
    assert expected_path.exists(), (
        f"Skill should be in global_learned by default. " f"global_learned={manager.global_learned}"
    )


def test_list_skills_aggregation(manager):
    """Verify list_skills aggregates from all layers."""
    manager.ensure_global_structure()
    manager.setup_project_structure()

    (manager.global_builtin / "b.md").write_text("content")
    (manager.global_learned / "l.md").write_text("content")
    (manager.project_local_dir / "p.md").write_text("content")

    skills = manager.list_skills()

    assert "b" in skills and skills["b"]["type"] == "builtin"
    assert "l" in skills and skills["l"]["type"] == "learned"
    assert "p" in skills and skills["p"]["type"] == "project"

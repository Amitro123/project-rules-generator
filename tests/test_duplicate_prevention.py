"""Tests for duplicate skill prevention.

Verifies that the system correctly detects existing skills and
prevents duplicate creation unless force=True is passed.
"""
import pytest
from pathlib import Path

from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator
from generator.skills_manager import SkillsManager


# ─── SkillDiscovery.skill_exists() ────────────────────────────────────────────

class TestSkillExists:
    """Unit tests for SkillDiscovery.skill_exists()."""

    def test_flat_file_detected(self, tmp_path):
        """skill_exists returns True for a flat .md file."""
        learned = tmp_path / "learned"
        learned.mkdir()
        (learned / "my-skill.md").write_text("# My Skill")

        discovery = _make_discovery(tmp_path)
        assert discovery.skill_exists("my-skill", scope="learned") is True

    def test_directory_format_detected(self, tmp_path):
        """skill_exists returns True for a directory/SKILL.md format."""
        learned = tmp_path / "learned"
        skill_dir = learned / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# My Skill")

        discovery = _make_discovery(tmp_path)
        assert discovery.skill_exists("my-skill", scope="learned") is True

    def test_missing_skill_returns_false(self, tmp_path):
        """skill_exists returns False when skill doesn't exist."""
        (tmp_path / "learned").mkdir()
        discovery = _make_discovery(tmp_path)
        assert discovery.skill_exists("nonexistent", scope="learned") is False

    def test_directory_without_skill_md_not_detected(self, tmp_path):
        """A directory without SKILL.md is NOT counted as a skill."""
        learned = tmp_path / "learned"
        (learned / "empty-dir").mkdir(parents=True)

        discovery = _make_discovery(tmp_path)
        assert discovery.skill_exists("empty-dir", scope="learned") is False

    def test_builtin_scope(self, tmp_path):
        """skill_exists works for builtin scope."""
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        (builtin / "core-skill.md").write_text("# Core Skill")

        discovery = _make_discovery(tmp_path)
        assert discovery.skill_exists("core-skill", scope="builtin") is True

    def test_invalid_scope_raises(self, tmp_path):
        """skill_exists raises ValueError for unknown scope."""
        discovery = _make_discovery(tmp_path)
        with pytest.raises(ValueError, match="Unknown scope"):
            discovery.skill_exists("any", scope="invalid")


# ─── SkillGenerator.create_skill() duplicate guard ────────────────────────────

class TestCreateSkillDuplicatePrevention:
    """Tests for the force=False duplicate guard in create_skill."""

    def test_skip_if_already_exists(self, tmp_path, capsys):
        """create_skill skips creation when skill already exists (force=False)."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        # Pre-create the skill as a flat file
        (discovery.global_learned / "test-skill.md").write_text("# Existing")

        generator = SkillGenerator(discovery)
        result = generator.create_skill("test-skill", force=False)

        captured = capsys.readouterr()
        assert "already exists" in captured.out
        assert "skipping" in captured.out

        # Content should NOT have been overwritten
        content = (discovery.global_learned / "test-skill.md").read_text()
        assert content == "# Existing"

    def test_force_overwrites_existing(self, tmp_path):
        """create_skill overwrites when force=True."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        # Pre-create the skill
        (discovery.global_learned / "test-skill.md").write_text("# Old Content")

        generator = SkillGenerator(discovery)
        generator.create_skill("test-skill", force=True)

        # The generator prefers project local path if available
        skill_file = discovery.project_learned_link / "test-skill" / "SKILL.md"
        assert skill_file.exists()

    def test_new_skill_created_normally(self, tmp_path):
        """create_skill creates a new skill when it doesn't exist."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        generator = SkillGenerator(discovery)
        result = generator.create_skill("brand-new-skill")

        assert (discovery.project_learned_link / "brand-new-skill" / "SKILL.md").exists()

    def test_name_normalization_prevents_duplicates(self, tmp_path, capsys):
        """Names like 'My Skill' and 'my-skill' resolve to the same normalized name."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        # Create with normalized name
        (discovery.global_learned / "my-skill.md").write_text("# My Skill")

        generator = SkillGenerator(discovery)
        # Try to create with spaces — should normalize to 'my-skill' and skip
        generator.create_skill("My Skill", force=False)

        captured = capsys.readouterr()
        assert "already exists" in captured.out


# ─── CoworkSkillCreator.exists_in_learned() ───────────────────────────────────

class TestExistsInLearned:
    """Tests for CoworkSkillCreator.exists_in_learned() delegation."""

    def test_delegates_to_skill_exists(self, tmp_path):
        """exists_in_learned uses SkillDiscovery.skill_exists() under the hood."""
        from generator.skill_creator import CoworkSkillCreator

        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        creator = CoworkSkillCreator(project_path=tmp_path)
        creator.discovery = discovery  # inject test discovery

        # Create skill in flat format
        (discovery.global_learned / "pytest-workflow.md").write_text("# Pytest")

        assert creator.exists_in_learned("pytest-workflow") is True
        assert creator.exists_in_learned("nonexistent-skill") is False

    def test_detects_directory_format(self, tmp_path):
        """exists_in_learned detects directory/SKILL.md format."""
        from generator.skill_creator import CoworkSkillCreator

        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        creator = CoworkSkillCreator(project_path=tmp_path)
        creator.discovery = discovery

        # Create skill in directory format
        skill_dir = discovery.global_learned / "docker-workflow"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Docker")

        assert creator.exists_in_learned("docker-workflow") is True


# ─── SkillsManager facade ─────────────────────────────────────────────────────

class TestSkillsManagerDuplicatePrevention:
    """Tests for duplicate prevention through the SkillsManager facade."""

    def test_create_skill_skips_existing(self, tmp_path, capsys):
        """SkillsManager.create_skill skips if skill already exists."""
        manager = SkillsManager(project_path=tmp_path)
        manager.ensure_global_structure()

        # Pre-create
        (manager.global_learned / "existing-skill.md").write_text("# Existing")

        manager.create_skill("existing-skill", force=False)

        captured = capsys.readouterr()
        assert "already exists" in captured.out

    def test_create_skill_force_overwrites(self, tmp_path):
        """SkillsManager.create_skill with force=True overwrites."""
        manager = SkillsManager(project_path=tmp_path)
        manager.ensure_global_structure()

        (manager.global_learned / "existing-skill.md").write_text("# Old")

        manager.create_skill("existing-skill", force=True)

        # New directory format created in PROJECT scope
        assert (manager.project_learned_link / "existing-skill" / "SKILL.md").exists()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_discovery(tmp_path: Path) -> SkillDiscovery:
    """Create a SkillDiscovery instance pointing to tmp_path directories."""
    discovery = SkillDiscovery.__new__(SkillDiscovery)
    discovery.project_path = tmp_path
    discovery.global_root = tmp_path
    discovery.global_learned = tmp_path / "learned"
    discovery.global_builtin = tmp_path / "builtin"
    discovery.package_builtin = tmp_path / "package_builtin"
    discovery.project_skills_root = tmp_path / ".clinerules" / "skills"
    discovery.project_local_dir = discovery.project_skills_root / "project"
    discovery.project_learned_link = discovery.project_skills_root / "learned"
    discovery.project_builtin_link = discovery.project_skills_root / "builtin"
    discovery._skills_cache = None  # Required by main's caching optimization

    # Create base dirs
    discovery.global_learned.mkdir(parents=True, exist_ok=True)
    discovery.global_builtin.mkdir(parents=True, exist_ok=True)

    return discovery

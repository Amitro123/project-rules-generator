"""Coverage boost: cli/migrate_standard.py (0% covered, 49 miss)."""

from pathlib import Path

import pytest

from cli.migrate_standard import merge_directories, migrate_project


class TestMergeDirectories:
    def test_creates_destination_if_missing(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.md").write_text("content")
        dst = tmp_path / "dst"

        merge_directories(src, dst)
        assert dst.exists()

    def test_moves_file_to_destination(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "skill.md").write_text("# Skill")
        dst = tmp_path / "dst"

        merge_directories(src, dst)
        assert (dst / "skill.md").exists()
        assert (dst / "skill.md").read_text() == "# Skill"

    def test_skips_existing_destination_file(self, tmp_path, capsys):
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.md").write_text("source content")
        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "file.md").write_text("existing content")

        merge_directories(src, dst)
        assert (dst / "file.md").read_text() == "existing content"
        captured = capsys.readouterr()
        assert "Skipping" in captured.out

    def test_merges_subdirectory(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        subdir = src / "subdir"
        subdir.mkdir()
        (subdir / "nested.md").write_text("nested")
        dst = tmp_path / "dst"

        merge_directories(src, dst)
        assert (dst / "subdir" / "nested.md").exists()

    def test_removes_empty_source_subdir_after_merge(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        subdir = src / "subdir"
        subdir.mkdir()
        (subdir / "file.md").write_text("content")
        dst = tmp_path / "dst"

        merge_directories(src, dst)
        # Source subdir should have been removed (rmdir on empty)
        assert not subdir.exists()


class TestMigrateProject:
    def test_creates_clinerules_dir(self, tmp_path):
        migrate_project(str(tmp_path))
        assert (tmp_path / ".clinerules").exists()

    def test_migrates_root_skills_to_clinerules(self, tmp_path):
        root_skills = tmp_path / "skills"
        root_skills.mkdir()
        (root_skills / "my-skill.md").write_text("# My Skill")

        migrate_project(str(tmp_path))
        assert (tmp_path / ".clinerules" / "skills" / "my-skill.md").exists()

    def test_removes_empty_root_skills_after_migration(self, tmp_path):
        root_skills = tmp_path / "skills"
        root_skills.mkdir()
        (root_skills / "skill.md").write_text("# Skill")

        migrate_project(str(tmp_path))
        assert not root_skills.exists()

    def test_prints_no_root_skills_when_absent(self, tmp_path, capsys):
        migrate_project(str(tmp_path))
        captured = capsys.readouterr()
        assert "No root 'skills/'" in captured.out

    def test_fixes_nested_skills_skills(self, tmp_path, capsys):
        # Create .clinerules/skills/skills (nested)
        clinerules = tmp_path / ".clinerules"
        clinerules.mkdir()
        nested = clinerules / "skills" / "skills"
        nested.mkdir(parents=True)
        (nested / "inner.md").write_text("# Inner Skill")

        migrate_project(str(tmp_path))
        captured = capsys.readouterr()
        assert "nested" in captured.out.lower()
        # Inner file should be moved up one level
        assert (clinerules / "skills" / "inner.md").exists()

    def test_handles_non_empty_root_skills(self, tmp_path, capsys):
        root_skills = tmp_path / "skills"
        root_skills.mkdir()
        (root_skills / "a.md").write_text("A")
        (root_skills / "b.md").write_text("B")

        # Pre-fill one dest file to simulate non-empty scenario
        target = tmp_path / ".clinerules" / "skills"
        target.mkdir(parents=True)
        (target / "a.md").write_text("existing A")

        migrate_project(str(tmp_path))
        captured = capsys.readouterr()
        # Should have printed some status
        assert "Migration complete" in captured.out

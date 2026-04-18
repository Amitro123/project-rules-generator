"""Tests for file operations utilities."""

import pytest

from prg_utils.file_ops import atomic_write_text, ensure_dir, file_exists, read_file, save_markdown


def test_read_file(tmp_path):
    """Test reading file content."""
    test_file = tmp_path / "test.txt"
    content = "Hello, World!"
    test_file.write_text(content, encoding="utf-8")

    assert read_file(test_file) == content
    assert read_file(str(test_file)) == content


def test_read_file_not_found(tmp_path):
    """Test reading non-existent file raises error."""
    non_existent = tmp_path / "non_existent.txt"
    with pytest.raises(FileNotFoundError):
        read_file(non_existent)


def test_save_markdown(tmp_path):
    """Test saving markdown content."""
    test_file = tmp_path / "test.md"
    content = "# Test\n\nContent"

    save_markdown(test_file, content)

    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == content


def test_save_markdown_creates_parents(tmp_path):
    """Test saving markdown creates parent directories."""
    test_file = tmp_path / "subdir" / "test.md"
    content = "# Test"

    save_markdown(test_file, content)

    assert test_file.exists()
    assert test_file.parent.exists()
    assert test_file.read_text(encoding="utf-8") == content


def test_file_exists(tmp_path):
    """Test checking if file exists."""
    test_file = tmp_path / "test.txt"
    test_file.touch()

    assert file_exists(test_file)
    assert file_exists(str(test_file))
    assert not file_exists(tmp_path / "non_existent.txt")


def test_atomic_write_text_creates_new_file(tmp_path):
    """atomic_write_text writes content to a new file and leaves no temp files."""
    target = tmp_path / "new.md"
    atomic_write_text(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith("new.md.") and p.name.endswith(".tmp")]
    assert leftovers == []


def test_atomic_write_text_no_backup_by_default(tmp_path):
    """Default write does not create a .bak even when overwriting."""
    target = tmp_path / "rules.md"
    target.write_text("original", encoding="utf-8")
    atomic_write_text(target, "updated")
    assert target.read_text(encoding="utf-8") == "updated"
    assert not (tmp_path / "rules.md.bak").exists()


def test_atomic_write_text_backup_preserves_prior_contents(tmp_path):
    """When backup=True and target exists, the prior contents are preserved at <path>.bak."""
    target = tmp_path / "rules.md"
    target.write_text("first revision", encoding="utf-8")

    backup_path = atomic_write_text(target, "second revision", backup=True)

    assert target.read_text(encoding="utf-8") == "second revision"
    assert backup_path == tmp_path / "rules.md.bak"
    assert backup_path.read_text(encoding="utf-8") == "first revision"


def test_atomic_write_text_backup_skipped_when_target_missing(tmp_path):
    """No backup is written if the target doesn't already exist."""
    target = tmp_path / "rules.md"
    backup_path = atomic_write_text(target, "fresh content", backup=True)
    assert backup_path is None
    assert target.read_text(encoding="utf-8") == "fresh content"
    assert not (tmp_path / "rules.md.bak").exists()


def test_atomic_write_text_overwrites_previous_backup(tmp_path):
    """Second backed-up write overwrites the prior .bak — only most recent kept."""
    target = tmp_path / "rules.md"
    target.write_text("v1", encoding="utf-8")
    atomic_write_text(target, "v2", backup=True)
    atomic_write_text(target, "v3", backup=True)

    assert target.read_text(encoding="utf-8") == "v3"
    # Backup now holds v2 (the revision immediately before v3), not v1.
    assert (tmp_path / "rules.md.bak").read_text(encoding="utf-8") == "v2"


def test_save_markdown_with_backup_flag(tmp_path):
    """save_markdown passes backup through to atomic_write_text."""
    target = tmp_path / "rules.md"
    target.write_text("before", encoding="utf-8")
    save_markdown(target, "after", backup=True)
    assert target.read_text(encoding="utf-8") == "after"
    assert (tmp_path / "rules.md.bak").read_text(encoding="utf-8") == "before"


def test_ensure_dir(tmp_path):
    """Test ensuring directory exists."""
    test_dir = tmp_path / "subdir"

    # Should create directory
    result = ensure_dir(test_dir)
    assert test_dir.exists()
    assert test_dir.is_dir()
    assert result == test_dir

    # Should handle existing directory
    result = ensure_dir(test_dir)
    assert test_dir.exists()
    assert result == test_dir

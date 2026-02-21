"""Tests for file operations utilities."""

from pathlib import Path

import pytest

from prg_utils.file_ops import ensure_dir, file_exists, read_file, save_markdown


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

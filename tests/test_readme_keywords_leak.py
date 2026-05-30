"""Tests that [project].keywords in pyproject.toml don't leak into tech detection.

A project that *documents* a technology in its keywords (e.g. a tool that is
*about* TypeScript and Docker) must not be detected as *depending* on it. Only
real dependency declarations should confirm a tech.

The fix lives in ``generator/analyzers/readme_parser.py``: ``_strip_keywords_field``
removes the keywords array before the dep-content scan.
"""

from __future__ import annotations

from generator.analyzers.readme_parser import _strip_keywords_field, _validate_tech_with_deps


def test_strip_removes_single_line_keywords():
    raw = 'keywords = ["typescript", "docker", "cli"]\ndependencies = ["click"]\n'
    out = _strip_keywords_field(raw.lower())
    assert "typescript" not in out
    assert "docker" not in out
    assert "click" in out  # real dep survives


def test_strip_removes_multiline_keywords():
    raw = "keywords = [\n" '    "typescript",\n' '    "docker",\n' "]\n" 'dependencies = ["fastapi"]\n'
    out = _strip_keywords_field(raw.lower())
    assert "typescript" not in out
    assert "docker" not in out
    assert "fastapi" in out


def test_keyword_only_tech_not_confirmed(tmp_path):
    """A pyproject that lists docker only in keywords must not confirm docker."""
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n" 'name = "prg"\n' 'keywords = ["docker", "typescript"]\n' 'dependencies = ["click"]\n',
        encoding="utf-8",
    )
    result = _validate_tech_with_deps(["python"], tmp_path)
    assert "docker" not in result
    assert "typescript" not in result


def test_real_dependency_still_confirmed(tmp_path):
    """A genuine dependency is still detected after keyword stripping."""
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n" 'name = "svc"\n' 'keywords = ["docker"]\n' 'dependencies = ["fastapi", "click"]\n',
        encoding="utf-8",
    )
    result = _validate_tech_with_deps([], tmp_path)
    assert "fastapi" in result
    assert "docker" not in result

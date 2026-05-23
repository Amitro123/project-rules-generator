"""Tests for the default tag-resolver (Phase 4b).

The resolver bridges PRG's skill storage (SKILL.md files with YAML
frontmatter) to the generic filter primitive in ``project_profile``.
These tests use a custom ``path_resolver`` so they don't depend on the
global ~/.project-rules-generator/ tree — proves the resolver factory
is dependency-injectable and the file-parsing logic is correct.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from generator.skills.tag_resolver import _tags_from_file, clear_tag_cache, default_tag_resolver


@pytest.fixture(autouse=True)
def _isolate_cache():
    """Each test starts with a fresh cache so file rewrites between
    test cases don't leak across the suite."""
    clear_tag_cache()
    yield
    clear_tag_cache()


def _write_skill(path: Path, *, tags=None, body: str = "skill body") -> Path:
    """Write a synthetic SKILL.md with frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if tags is None:
        text = f"{body}\n"
    else:
        tags_yaml = "\n".join(f"  - {t}" for t in tags)
        text = f"---\nname: x\ntags:\n{tags_yaml}\n---\n{body}\n"
    path.write_text(text, encoding="utf-8")
    return path


# --- File-level tag extraction ---------------------------------------------


def test_tags_extracted_from_markdown_frontmatter(tmp_path: Path):
    skill = _write_skill(tmp_path / "SKILL.md", tags=["fastapi", "python", "async"])
    tags = _tags_from_file(str(skill))
    assert tags == frozenset({"fastapi", "python", "async"})


def test_tags_lowercased_on_read(tmp_path: Path):
    """Frontmatter tags can be any case; resolver normalises to lowercase
    so the filter's case-insensitive intersection works correctly."""
    skill = _write_skill(tmp_path / "SKILL.md", tags=["FastAPI", "PYTHON"])
    tags = _tags_from_file(str(skill))
    assert tags == frozenset({"fastapi", "python"})


def test_empty_tags_list_returns_empty_set(tmp_path: Path):
    skill = _write_skill(tmp_path / "SKILL.md", tags=[])
    assert _tags_from_file(str(skill)) == frozenset()


def test_no_tags_key_returns_empty(tmp_path: Path):
    """A SKILL.md with frontmatter but no `tags:` key produces empty."""
    skill = tmp_path / "SKILL.md"
    skill.write_text("---\nname: x\ndescription: a skill\n---\nbody\n", encoding="utf-8")
    assert _tags_from_file(str(skill)) == frozenset()


def test_no_frontmatter_at_all_returns_empty(tmp_path: Path):
    skill = _write_skill(tmp_path / "plain.md", tags=None)
    assert _tags_from_file(str(skill)) == frozenset()


def test_malformed_frontmatter_returns_empty(tmp_path: Path):
    """A YAML syntax error inside the frontmatter block doesn't crash;
    the file is treated as having no tags."""
    skill = tmp_path / "SKILL.md"
    skill.write_text("---\ntags: [unclosed\n---\nbody\n", encoding="utf-8")
    assert _tags_from_file(str(skill)) == frozenset()


def test_missing_file_returns_empty(tmp_path: Path):
    """File doesn't exist → empty, no exception."""
    assert _tags_from_file(str(tmp_path / "does-not-exist.md")) == frozenset()


def test_pure_yaml_file_with_tags(tmp_path: Path):
    """A .yaml file with top-level `tags:` (no frontmatter markers) is
    also supported — some learned skills are YAML, not markdown."""
    skill = tmp_path / "skill.yaml"
    skill.write_text("name: y\ntags:\n  - vue\n  - typescript\n", encoding="utf-8")
    assert _tags_from_file(str(skill)) == frozenset({"vue", "typescript"})


def test_tags_value_not_a_list_returns_empty(tmp_path: Path):
    """If `tags:` is somehow a string or int instead of a list, treat
    as empty rather than splitting/crashing."""
    skill = tmp_path / "SKILL.md"
    skill.write_text("---\ntags: just-a-string\n---\n", encoding="utf-8")
    assert _tags_from_file(str(skill)) == frozenset()


def test_non_string_items_in_tags_list_are_skipped(tmp_path: Path):
    """Mixed-type tags list keeps the strings, drops the rest."""
    skill = tmp_path / "SKILL.md"
    skill.write_text("---\ntags:\n  - good\n  - 42\n  - null\n  - also-good\n---\n", encoding="utf-8")
    assert _tags_from_file(str(skill)) == frozenset({"good", "also-good"})


# --- Resolver factory ------------------------------------------------------


def test_default_resolver_uses_injected_path_resolver(tmp_path: Path):
    """The factory's `path_resolver` parameter lets tests substitute a
    custom (skill_ref) -> Path mapping without touching SkillPathManager."""
    fastapi_skill = _write_skill(tmp_path / "fastapi.md", tags=["fastapi", "python"])

    def _custom_path_resolver(ref: str) -> Optional[Path]:
        if ref == "learned/fastapi/async-patterns":
            return fastapi_skill
        return None

    resolver = default_tag_resolver(path_resolver=_custom_path_resolver)
    assert resolver("learned/fastapi/async-patterns") == frozenset({"fastapi", "python"})
    # Unknown ref → resolver returns None → empty tags
    assert resolver("learned/unknown/skill") == frozenset()


def test_resolver_swallows_path_resolver_exceptions(tmp_path: Path):
    """If the injected path_resolver raises, the tag-resolver must not
    propagate the exception — it returns empty (conservative)."""

    def _broken(_ref):
        raise RuntimeError("path resolver broken")

    resolver = default_tag_resolver(path_resolver=_broken)
    assert resolver("learned/foo/bar") == frozenset()


def test_resolver_returns_empty_when_path_is_none(tmp_path: Path):
    """When the path_resolver returns None (skill not found on disk),
    the tag-resolver returns empty tags."""

    def _none(_ref):
        return None

    resolver = default_tag_resolver(path_resolver=_none)
    assert resolver("learned/anything") == frozenset()


# --- Cache behaviour -------------------------------------------------------


def test_cache_returns_old_value_until_cleared(tmp_path: Path):
    """The lru_cache means a second resolve of the same ref doesn't
    re-read the file. Tests that rewrite a fixture file mid-test must
    call clear_tag_cache() to see the new content."""
    skill = _write_skill(tmp_path / "SKILL.md", tags=["v1"])
    first = _tags_from_file(str(skill))
    assert first == frozenset({"v1"})

    # Rewrite the file
    _write_skill(skill, tags=["v2"])
    # Without clearing the cache, the old value is returned
    cached = _tags_from_file(str(skill))
    assert cached == frozenset({"v1"})

    # Clear and re-read → see the new value
    clear_tag_cache()
    fresh = _tags_from_file(str(skill))
    assert fresh == frozenset({"v2"})


# --- Integration with filter_skills_by_tech_overlap -----------------------


def test_resolver_composes_with_filter(tmp_path: Path):
    """End-to-end: the default resolver + the generic filter primitive
    drop a learned skill whose tags don't overlap project tech."""
    from generator.project_profile import filter_skills_by_tech_overlap

    jest_skill = _write_skill(tmp_path / "jest" / "SKILL.md", tags=["jest", "react"])
    fastapi_skill = _write_skill(tmp_path / "fastapi" / "SKILL.md", tags=["fastapi", "python"])

    def _path_resolver(ref: str) -> Optional[Path]:
        if "jest" in ref:
            return jest_skill
        if "fastapi" in ref:
            return fastapi_skill
        return None

    resolver = default_tag_resolver(path_resolver=_path_resolver)
    survivors, traces = filter_skills_by_tech_overlap(
        selected_refs={
            "learned/jest/snapshot",
            "learned/fastapi/async-patterns",
        },
        tech_stack={"python", "fastapi"},
        tag_resolver=resolver,
    )
    assert survivors == frozenset({"learned/fastapi/async-patterns"})
    assert len(traces) == 1
    assert traces[0].skill_ref == "learned/jest/snapshot"

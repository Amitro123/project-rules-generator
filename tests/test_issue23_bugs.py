"""
Tests for Issue #23 — Skills Mechanism: Bugs + Design Issues (post-v1.3)
=========================================================================

BUG-1  — create_skill() returns non-existent dir for flat-file skills
BUG-2  — Already resolved in current code (detect_skill_needs uses TECH_SKILL_NAMES)
BUG-3  — READMEStrategy.generate() embedded full README, bypassing quality size gate
BUG-4  — resolve_skill() missed dir-style skills in project layer

DESIGN-1 — create_skill() never called invalidate_cache() after creation
DESIGN-2 — link_from_learned() linked only SKILL.md, not the whole skill directory
DESIGN-3 — generate_from_readme() bypasses strategy chain (deferred — larger refactor)
"""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from generator.skill_creator import CoworkSkillCreator
from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_discovery(tmp_path: Path) -> SkillDiscovery:
    """Create a SkillDiscovery instance backed by tmp_path directories (with project paths)."""
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
    discovery._skills_cache = None

    discovery.global_learned.mkdir(parents=True, exist_ok=True)
    discovery.global_builtin.mkdir(parents=True, exist_ok=True)
    return discovery


def _make_discovery_global_only(tmp_path: Path) -> SkillDiscovery:
    """SkillDiscovery with NO project paths — create_skill() writes to global_learned,
    which is the same directory _build_cache() indexes for the 'learned' scope.
    Use this when testing global learned cache visibility (DESIGN-1).
    """
    discovery = SkillDiscovery.__new__(SkillDiscovery)
    discovery.project_path = None
    discovery.global_root = tmp_path
    discovery.global_learned = tmp_path / "learned"
    discovery.global_builtin = tmp_path / "builtin"
    discovery.package_builtin = tmp_path / "package_builtin"
    discovery.project_skills_root = None
    discovery.project_local_dir = None
    discovery.project_learned_link = None
    discovery.project_builtin_link = None
    discovery._skills_cache = None

    discovery.global_learned.mkdir(parents=True, exist_ok=True)
    discovery.global_builtin.mkdir(parents=True, exist_ok=True)
    return discovery


# ─── BUG-1 ───────────────────────────────────────────────────────────────────


class TestBug1FlatFileReturnPath:
    """BUG-1: create_skill() flat-file early-return must not return a non-existent dir."""

    def test_flat_file_skill_returns_existing_parent_not_phantom_dir(self, tmp_path):
        """For a flat .md skill, create_skill() must return an existing path."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        # Pre-create a flat-file skill (NOT directory-style)
        flat = discovery.global_learned / "fastapi-endpoints.md"
        flat.write_text("# FastAPI Endpoints skill", encoding="utf-8")

        generator = SkillGenerator(discovery)
        result = generator.create_skill("fastapi-endpoints", force=False)

        # The returned path must actually exist on disk
        assert result.exists(), (
            f"BUG-1: create_skill() returned non-existent path {result!r} "
            "for a flat-file skill."
        )

    def test_flat_file_skill_does_not_return_phantom_suffix(self, tmp_path):
        """Regression: the bugged code returned `learned/fastapi-endpoints` (non-existent)."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()

        flat = discovery.global_learned / "my-skill.md"
        flat.write_text("# My Skill", encoding="utf-8")

        generator = SkillGenerator(discovery)
        result = generator.create_skill("my-skill", force=False)

        # Must NOT be the phantom `learned/my-skill` directory
        phantom = discovery.global_learned / "my-skill"
        assert result != phantom or phantom.exists(), (
            "BUG-1: returned the phantom non-existent directory path."
        )

    def test_directory_style_skill_still_returns_skill_dir(self, tmp_path):
        """Regression guard: dir-style skills in project scope must return the skill directory."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()
        discovery.project_local_dir.mkdir(parents=True, exist_ok=True)

        # Pre-create the skill in project_local_dir (project scope — where duplicate guard checks)
        skill_dir = discovery.project_local_dir / "docker-deployment"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Docker Deployment", encoding="utf-8")
        discovery._skills_cache = None  # force cache rebuild

        generator = SkillGenerator(discovery)
        result = generator.create_skill("docker-deployment", force=False)

        assert result == skill_dir, (
            f"Dir-style skill in project scope must return its directory, got {result!r}"
        )


# ─── BUG-3 ───────────────────────────────────────────────────────────────────


class TestBug3ReadmeContextTrimmed:
    """BUG-3: READMEStrategy must not embed the full README in the skill body.

    New behavior: READMEStrategy returns None when the skill name words don't
    appear in the extracted purpose (relevance check). Tests must use skill names
    whose significant words (>3 chars) appear in the README purpose/description.
    """

    def _make_long_project_readme(self, length: int = 2000) -> str:
        """README whose purpose mentions 'project' — matches skill name 'project-workflow'."""
        return (
            "# Project Workflow Tool\n\n"
            "Automates the project workflow with intelligent analysis.\n\n"
            + "A" * length
        )

    def test_context_section_capped_at_400_chars(self, tmp_path):
        """Generated skill body must contain at most 400 chars of README context."""
        from generator.strategies.readme_strategy import READMEStrategy

        long_readme = self._make_long_project_readme(2000)
        strategy = READMEStrategy()
        # "project" and "workflow" both appear in the README purpose
        content = strategy.generate("project-workflow", tmp_path, long_readme, "groq")

        assert content is not None, (
            "READMEStrategy returned None unexpectedly. "
            "Ensure the skill name words appear in the README purpose."
        )

        # Extract everything after "## Context"
        idx = content.find("## Context")
        assert idx != -1, "## Context section not found."
        context_slice = content[idx:]

        # The README body after the section header should be ≤ 400 chars of actual README text
        # (the header + truncation note + newlines account for ~80 chars of overhead)
        assert len(context_slice) < 600, (
            f"BUG-3: Context section is {len(context_slice)} chars — full README still embedded."
        )

    def test_short_readme_not_truncated(self, tmp_path):
        """Short READMEs (≤ 400 chars) must be included in full without truncation note."""
        from generator.strategies.readme_strategy import READMEStrategy

        # "project" appears in the purpose so the relevance check passes
        short_readme = "# Project Tool\n\nA project management tool for short descriptions.\n"
        strategy = READMEStrategy()
        content = strategy.generate("project-tool", tmp_path, short_readme, "groq")

        assert content is not None, (
            "READMEStrategy returned None unexpectedly for relevant skill name."
        )
        assert "truncated" not in content, (
            "Short README must not be truncated."
        )

    def test_long_readme_includes_truncation_note(self, tmp_path):
        """Long READMEs must mention truncation so agents know to check the source."""
        from generator.strategies.readme_strategy import READMEStrategy

        long_readme = self._make_long_project_readme(2000)
        strategy = READMEStrategy()
        # "project" and "workflow" both appear in the README purpose
        content = strategy.generate("project-workflow", tmp_path, long_readme, "groq")

        assert content is not None, (
            "READMEStrategy returned None unexpectedly for relevant skill name."
        )
        assert "truncated" in content.lower() or "README.md" in content, (
            "BUG-3: Long README embedded without any truncation notice."
        )

    def test_irrelevant_skill_name_returns_none(self, tmp_path):
        """Relevance check: skill name words absent from purpose must return None."""
        from generator.strategies.readme_strategy import READMEStrategy

        readme = "# Project Tool\n\nAutomates project workflows.\n"
        strategy = READMEStrategy()
        # "readme" and "improvement" do not appear in the purpose above
        content = strategy.generate("readme-improvement", tmp_path, readme, "groq")

        assert content is None, (
            "READMEStrategy must return None when skill name words are absent from the README purpose."
        )


# ─── BUG-4 ───────────────────────────────────────────────────────────────────


class TestBug4ProjectLayerDirStyleSkill:
    """BUG-4: resolve_skill() must find dir-style skills in the project layer."""

    def test_project_layer_flat_file_found(self, tmp_path):
        """Regression guard: flat .md in project layer still resolves correctly."""
        discovery = _make_discovery(tmp_path)
        discovery.project_local_dir.mkdir(parents=True, exist_ok=True)

        flat = discovery.project_local_dir / "my-skill.md"
        flat.write_text("# My Skill", encoding="utf-8")
        discovery._skills_cache = None  # force rebuild

        result = discovery.resolve_skill("my-skill")
        assert result == flat, f"Flat-file skill in project layer not found, got {result!r}"

    def test_project_layer_dir_style_skill_found(self, tmp_path):
        """BUG-4: dir-style skill in project layer must be resolved by resolve_skill()."""
        discovery = _make_discovery(tmp_path)
        discovery.project_local_dir.mkdir(parents=True, exist_ok=True)

        skill_dir = discovery.project_local_dir / "my-dir-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# My Dir Skill", encoding="utf-8")
        discovery._skills_cache = None

        result = discovery.resolve_skill("my-dir-skill")
        assert result == skill_md, (
            f"BUG-4: dir-style skill in project layer was not found, got {result!r}"
        )

    def test_project_layer_takes_priority_over_learned(self, tmp_path):
        """Project-layer dir-style skill must shadow learned-layer flat skill."""
        discovery = _make_discovery(tmp_path)
        discovery.project_local_dir.mkdir(parents=True, exist_ok=True)

        # Learned layer flat file
        (discovery.global_learned / "shared-skill.md").write_text("# Learned", encoding="utf-8")

        # Project layer dir-style override
        skill_dir = discovery.project_local_dir / "shared-skill"
        skill_dir.mkdir()
        project_md = skill_dir / "SKILL.md"
        project_md.write_text("# Project Override", encoding="utf-8")
        discovery._skills_cache = None

        result = discovery.resolve_skill("shared-skill")
        assert result == project_md, (
            f"BUG-4: project dir-style skill did not override learned flat skill. Got {result!r}"
        )


# ─── DESIGN-1 ─────────────────────────────────────────────────────────────────


class TestDesign1CacheInvalidatedAfterCreate:
    """DESIGN-1: create_skill() must call invalidate_cache() so callers see the new skill."""

    def test_skill_visible_in_list_skills_immediately_after_create(self, tmp_path):
        """After create_skill(), list_skills() must include the new skill without manual invalidation.

        We use a discovery with no project_learned_link so create_skill() writes
        to global_learned — the same directory _build_cache() indexes for the
        'learned' layer, making the new skill visible after a cache rebuild.
        """
        discovery = _make_discovery_global_only(tmp_path)
        discovery.ensure_global_structure()

        # Prime the cache (empty)
        initial = discovery.list_skills()

        generator = SkillGenerator(discovery)
        generator.create_skill("fresh-skill")

        # Without DESIGN-1 fix, the cache would still be stale and fresh-skill absent
        updated = discovery.list_skills()
        assert "fresh-skill" in updated, (
            "DESIGN-1: cache not invalidated — fresh-skill not visible in list_skills() "
            "immediately after create_skill()."
        )

    def test_cache_is_none_after_create_skill(self, tmp_path):
        """DESIGN-1: _skills_cache must be None (cleared) at the end of create_skill()."""
        discovery = _make_discovery_global_only(tmp_path)
        discovery.ensure_global_structure()

        # Prime the cache
        _ = discovery.list_skills()
        assert discovery._skills_cache is not None

        generator = SkillGenerator(discovery)
        generator.create_skill("another-skill")

        assert discovery._skills_cache is None, (
            "DESIGN-1: create_skill() did not call invalidate_cache()."
        )


# ─── DESIGN-2 ─────────────────────────────────────────────────────────────────


class TestDesign2LinkFromLearnedDirectory:
    """DESIGN-2: link_from_learned() must link the entire dir for directory-style skills."""

    def test_flat_skill_still_linked_as_flat_file(self, tmp_path):
        """Regression guard: flat-file skills should still be linked as flat .md."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()
        discovery.project_local_dir.mkdir(parents=True, exist_ok=True)

        flat = discovery.global_learned / "flat-skill.md"
        flat.write_text("# Flat", encoding="utf-8")

        creator = CoworkSkillCreator(project_path=tmp_path)
        creator.discovery = discovery

        # Ensure project_local_dir exists (link_from_learned requires it)
        assert discovery.project_local_dir.exists(), "project_local_dir must exist before linking"
        creator.link_from_learned("flat-skill")

        target = discovery.project_local_dir / "flat-skill.md"
        assert target.exists(), (
            f"Flat-file skill was not linked to project local dir. "
            f"_link_or_copy must fall back to shutil.copy2 for flat files on Windows."
        )

    def test_dir_style_skill_directory_is_linked(self, tmp_path):
        """DESIGN-2: a directory-style skill's entire dir must be linked (not just SKILL.md)."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()
        discovery.project_local_dir.mkdir(parents=True, exist_ok=True)

        # Create a directory-style skill with Level-3 subdirs
        skill_dir = discovery.global_learned / "docker-deployment"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Docker Deployment", encoding="utf-8")
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "validate.sh").write_text("#!/bin/bash\necho ok", encoding="utf-8")

        creator = CoworkSkillCreator(project_path=tmp_path)
        creator.discovery = discovery
        creator.link_from_learned("docker-deployment")

        target_dir = discovery.project_local_dir / "docker-deployment"
        assert target_dir.exists(), (
            "DESIGN-2: directory-style skill was not linked as a directory."
        )
        assert (target_dir / "SKILL.md").exists(), "SKILL.md missing from linked dir."

    def test_dir_style_skill_subdirs_are_accessible(self, tmp_path):
        """DESIGN-2: Level-3 subdirs (scripts/, references/) must be accessible after link."""
        discovery = _make_discovery(tmp_path)
        discovery.ensure_global_structure()
        discovery.project_local_dir.mkdir(parents=True, exist_ok=True)

        skill_dir = discovery.global_learned / "fastapi-endpoints"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# FastAPI Endpoints", encoding="utf-8")
        scripts = skill_dir / "scripts"
        scripts.mkdir()
        (scripts / "generate.py").write_text("# generate helper", encoding="utf-8")
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "api-reference.md").write_text("# API Ref", encoding="utf-8")

        creator = CoworkSkillCreator(project_path=tmp_path)
        creator.discovery = discovery
        creator.link_from_learned("fastapi-endpoints")

        linked_scripts = discovery.project_local_dir / "fastapi-endpoints" / "scripts"
        linked_refs = discovery.project_local_dir / "fastapi-endpoints" / "references"
        assert linked_scripts.exists(), "DESIGN-2: scripts/ subdir not linked."
        assert linked_refs.exists(), "DESIGN-2: references/ subdir not linked."

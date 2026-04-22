"""Tests for scratch/placeholder skill-name refusal (OSS-audit Blocker #3).

The generator must refuse to create skills whose names look like developer
throwaways, so we don't ship files like `temp_test_project-workflow.md`
that leaked into the repo pre-open-source.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator


def _make_generator(tmp_path: Path) -> SkillGenerator:
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
    discovery.project_local_dir.mkdir(parents=True, exist_ok=True)
    return SkillGenerator(discovery)


@pytest.mark.parametrize(
    "bad_name",
    [
        "temp-foo",
        "temp_test_project-workflow",  # the exact leaker from the audit
        "tmp-thing",
        "scratch-pad",
        "placeholder-api",
        "draft-skill",
        "temp",
        "scratch",
    ],
)
def test_refuses_scratch_names(tmp_path, bad_name):
    """Scratch/temp-prefixed skill names must raise before any file is written."""
    generator = _make_generator(tmp_path)
    with pytest.raises(ValueError, match="scratch/placeholder name"):
        generator.create_skill(bad_name)


@pytest.mark.parametrize(
    "good_name",
    [
        # False positives the refusal must NOT trip over.
        "temperature-gauge",
        "template-engine",
        "draftkings-api",
        "scratchpad-editor",  # compound word, not 'scratch-'
        "tmpfs-mount",  # compound, not 'tmp-'
        "placeholderless-input",
    ],
)
def test_allows_legitimate_names_with_similar_prefix(tmp_path, good_name, monkeypatch):
    """Names that merely start with the same letters (temperature, template…) must pass."""
    generator = _make_generator(tmp_path)
    # Short-circuit the strategy chain so the test doesn't need a real project.
    monkeypatch.setattr(generator, "_run_strategy_chain", lambda *a, **kw: "# stub\n")
    path = generator.create_skill(good_name)
    assert path.exists()

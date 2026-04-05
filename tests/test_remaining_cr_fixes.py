"""Regression tests for the second wave of CR fixes.

Covers:
  1. All builtin skill files have YAML frontmatter (Issue 7)
  2. AgentExecutor.match_skill() synonym expansion (Issue 4)
"""

import json
from pathlib import Path

import pytest

from generator.planning.agent_executor import AgentExecutor, _expand_input

# ---------------------------------------------------------------------------
# Issue 7 — Builtin skills must have YAML frontmatter
# ---------------------------------------------------------------------------


BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "generator" / "skills" / "builtin"


def _collect_builtin_skills():
    """Enumerate all builtin skill files (.md and SKILL.md)."""
    paths = []
    # Flat .md files
    for p in BUILTIN_SKILLS_DIR.glob("*.md"):
        paths.append(p)
    # Folder-based SKILL.md files (any depth)
    for p in BUILTIN_SKILLS_DIR.rglob("SKILL.md"):
        paths.append(p)
    return paths


@pytest.mark.parametrize(
    "skill_path", _collect_builtin_skills(), ids=lambda p: p.name if p.name != "SKILL.md" else p.parent.name
)
def test_builtin_skill_has_yaml_frontmatter(skill_path):
    """Every builtin skill must start with --- YAML frontmatter block."""
    content = skill_path.read_text(encoding="utf-8")
    assert content.startswith("---"), (
        f"{skill_path.relative_to(BUILTIN_SKILLS_DIR)} missing YAML frontmatter.\n"
        "Add a --- ... --- block at the top with at least 'name', 'description', and 'tools'."
    )
    # The frontmatter must close
    close_pos = content.find("\n---", 3)
    assert close_pos != -1, f"{skill_path.relative_to(BUILTIN_SKILLS_DIR)} has unclosed frontmatter block."


@pytest.mark.parametrize(
    "skill_path", _collect_builtin_skills(), ids=lambda p: p.name if p.name != "SKILL.md" else p.parent.name
)
def test_builtin_skill_frontmatter_has_when_trigger(skill_path):
    """Builtin skill description field must contain at least one 'When ...' line."""
    import yaml

    content = skill_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        pytest.skip("No frontmatter — covered by test_builtin_skill_has_yaml_frontmatter")
    end = content.find("\n---", 3)
    if end == -1:
        pytest.skip("Frontmatter unclosed")
    yaml_block = content[3:end].strip()
    meta = yaml.safe_load(yaml_block) or {}
    desc = meta.get("description", "")
    lines = [ln.strip() for ln in str(desc).splitlines() if ln.strip()]
    has_when = any(ln.lower().startswith("when") for ln in lines)
    assert has_when, (
        f"{skill_path.relative_to(BUILTIN_SKILLS_DIR)} description lacks 'When ...' trigger lines.\n"
        "Add at least one line starting with 'When the user ...' in the description field."
    )


# ---------------------------------------------------------------------------
# Issue 4 — Synonym expansion in trigger matching
# ---------------------------------------------------------------------------


class TestSynonymExpansion:
    def test_regression_expands_to_bug(self):
        expanded = _expand_input("there's a regression in the auth module")
        assert "bug" in expanded

    def test_ci_is_red_expands_to_bug_error(self):
        expanded = _expand_input("CI is red")
        assert "bug" in expanded
        assert "error" in expanded

    def test_nothing_works_expands(self):
        expanded = _expand_input("nothing works after the deployment")
        assert "bug" in expanded
        assert "not working" in expanded

    def test_pull_request_expands_to_review(self):
        expanded = _expand_input("I'm about to open a pull request")
        assert "ready for review" in expanded

    def test_pr_expands_to_review(self):
        expanded = _expand_input("I opened a PR for this")
        assert "ready for review" in expanded

    def test_clean_up_expands_to_refactor(self):
        expanded = _expand_input("let's clean up this old module")
        assert "refactor" in expanded

    def test_unchanged_when_no_synonyms(self):
        """Input without any synonym patterns should not be altered (just lowercased)."""
        expanded = _expand_input("fix a bug in the auth module")
        assert "fix a bug in the auth module" in expanded

    def test_lets_create_expands(self):
        expanded = _expand_input("let's create a login page")
        assert "i want to add" in expanded or "let's build" in expanded


class TestMatchSkillSynonymIntegration:
    def test_regression_matches_bug_skill(self, tmp_path):
        """'there's a regression' should match a skill that has 'bug' as a trigger phrase."""
        triggers_dir = tmp_path / ".clinerules"
        triggers_dir.mkdir()
        triggers_file = triggers_dir / "auto-triggers.json"
        triggers_file.write_text(
            json.dumps({"systematic-debugging": ["bug", "error", "not working"]}),
            encoding="utf-8",
        )

        executor = AgentExecutor(project_path=tmp_path)
        result = executor.match_skill("there's a regression in the auth module")
        assert result == "systematic-debugging"

    def test_ci_is_red_matches_debug_skill(self, tmp_path):
        """'CI is red' should match a debugging skill."""
        triggers_dir = tmp_path / ".clinerules"
        triggers_dir.mkdir()
        (triggers_dir / "auto-triggers.json").write_text(
            json.dumps({"systematic-debugging": ["bug", "failing test", "error"]}),
            encoding="utf-8",
        )

        executor = AgentExecutor(project_path=tmp_path)
        result = executor.match_skill("CI is red, nothing passes")
        assert result == "systematic-debugging"

    def test_exact_match_still_works(self, tmp_path):
        """Original exact match should still work after refactor."""
        triggers_dir = tmp_path / ".clinerules"
        triggers_dir.mkdir()
        (triggers_dir / "auto-triggers.json").write_text(
            json.dumps({"fix-bug": ["fix a bug"]}),
            encoding="utf-8",
        )

        executor = AgentExecutor(project_path=tmp_path)
        result = executor.match_skill("fix a bug in auth module")
        assert result == "fix-bug"

"""Regression tests for BUG_REPORT_AI_FLAG.md.

Pre-release blockers caught during end-to-end validation on three real
projects. See BUG_REPORT_AI_FLAG.md for full context.

- Bug A: `--ai` did not trigger project skill generation because
  `auto_generate_skills` stayed False unless `--provider` was also passed.
- Bug B: `generate_from_readme` wrote new skills to
  `~/.project-rules-generator/learned/` as a side effect of `prg analyze`,
  leaking project-specific content into unrelated projects.
- Bug C: empty/junk content (e.g. "content", "BUILTIN") could be written
  to skill files and then synced into every project's
  `.clinerules/skills/builtin/`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.analyze_helpers import normalize_analyze_options
from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator, _is_meaningful_skill_content


# ---------------------------------------------------------------------------
# Bug A — `--ai` must trigger auto_generate_skills even without --provider
# ---------------------------------------------------------------------------


def test_bug_a_ai_flag_alone_enables_auto_generate_skills():
    """`--ai` on its own (no --provider, no --mode) must flip
    auto_generate_skills to True so project/ is populated."""
    auto_skills, ai, constitution = normalize_analyze_options(
        mode=None,
        provider=None,
        auto_generate_skills=False,
        ai=True,
        constitution=False,
    )
    assert ai is True
    assert auto_skills is True, "Bug A regression: --ai did not enable auto_generate_skills"


def test_bug_a_mode_manual_wins_over_ai():
    """If mode='manual' is passed, --ai should not silently flip auto_generate_skills
    (explicit manual intent overrides)."""
    auto_skills, ai, _constitution = normalize_analyze_options(
        mode="manual",
        provider=None,
        auto_generate_skills=False,
        ai=True,
        constitution=False,
    )
    # ai stays whatever the user passed; auto_skills must remain False in manual mode
    assert auto_skills is False, "manual mode must suppress auto_generate_skills"


def test_bug_a_provider_still_implies_ai_and_auto_gen():
    """Regression: the pre-existing `--provider` → auto_gen rule still works."""
    auto_skills, ai, constitution = normalize_analyze_options(
        mode=None,
        provider="groq",
        auto_generate_skills=False,
        ai=False,
        constitution=False,
    )
    assert ai is True
    assert auto_skills is True
    assert constitution is True


# ---------------------------------------------------------------------------
# Bug B — generate_from_readme must not write to global_learned
# ---------------------------------------------------------------------------


def test_bug_b_create_branch_does_not_pollute_global_learned(tmp_path: Path):
    """When action=='create', the skill must be written ONLY to the
    project-local dir — never to ~/.project-rules-generator/learned/."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    global_learned = tmp_path / "global_learned"
    global_learned.mkdir()

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    discovery = MagicMock(spec=SkillDiscovery)
    discovery.project_local_dir = output_dir / "skills" / "project"
    discovery.project_local_dir.mkdir(parents=True)
    discovery.global_learned = global_learned
    # skill_exists returns False → action='create'
    discovery.skill_exists.return_value = False
    discovery.resolve_skill.return_value = None

    generator = SkillGenerator(discovery)

    # Mock the strategy chain so we get deterministic content (no LLM calls).
    with patch.object(
        SkillGenerator,
        "_run_strategy_chain",
        return_value="# Skill: Pytest Testing\n\nproject-specific pytest guidance\n",
    ):
        with patch.object(
            SkillGenerator, "check_global_skill_reuse", return_value={"pytest-testing": "create"}
        ):
            generated = generator.generate_from_readme(
                readme_content="# MyProject\nUses pytest.\n",
                tech_stack=["pytest"],
                output_dir=output_dir,
                project_name="myproject",
                project_path=project_path,
            )

    # Project-local write happened
    project_skill = discovery.project_local_dir / "pytest-testing" / "SKILL.md"
    assert project_skill.exists(), "project-local skill missing"
    assert "pytest-testing" in generated

    # Global learned must be UNTOUCHED — Bug B regression guard
    assert not (global_learned / "pytest-testing").exists(), (
        "Bug B regression: generate_from_readme wrote project-specific skill "
        "to ~/.project-rules-generator/learned/"
    )
    assert list(global_learned.iterdir()) == [], (
        f"Bug B regression: global_learned was touched — contents: "
        f"{list(global_learned.iterdir())}"
    )


# ---------------------------------------------------------------------------
# Bug C — content-validation guard
# ---------------------------------------------------------------------------


def test_bug_c_is_meaningful_skill_content_rejects_junk():
    """The guard must reject all the actual junk that was found in
    ~/.project-rules-generator/builtin/ (stale test pollution)."""
    # Empty-ish
    assert not _is_meaningful_skill_content(None)
    assert not _is_meaningful_skill_content("")
    assert not _is_meaningful_skill_content("   \n\n")
    # Bare words used by old tests (b.md, conflict-skill.md, etc.)
    assert not _is_meaningful_skill_content("content")
    assert not _is_meaningful_skill_content("BUILTIN")
    assert not _is_meaningful_skill_content("LEARNED")
    assert not _is_meaningful_skill_content("PROJECT")
    assert not _is_meaningful_skill_content("B")


def test_bug_c_is_meaningful_skill_content_accepts_real_skills():
    """The guard must accept real skills and minimal test mocks that have a heading."""
    # Deliberately-minimal test mock (used by test_skill_name_refusal.py)
    assert _is_meaningful_skill_content("# stub\n")
    # StubStrategy-style output
    assert _is_meaningful_skill_content("# Skill: Pytest Testing\n\n## Purpose\n\nFoo.\n")
    # Jinja2-style frontmatter + body
    assert _is_meaningful_skill_content(
        "---\nname: foo\n---\n\n# Skill: Foo\n\nBody.\n"
    )


# ---------------------------------------------------------------------------
# Bug H — bracketed-placeholder density guard
# ---------------------------------------------------------------------------


def test_bug_h_placeholder_content_rejected():
    """Files full of literal `[One sentence: ...]` brackets are stale
    templates and must be rejected even when they have a markdown heading."""
    content = (
        "# Skill: Gemini API\n"
        "## Purpose\n"
        "[One sentence: what problem does this solve and for whom.]\n\n"
        "## Steps\n"
        "1. [First step]\n"
        "2. [Second step]\n\n"
        "## Anti-patterns\n"
        "- [What NOT to do]\n"
    )
    assert not _is_meaningful_skill_content(content), (
        "Bug H regression: bracketed-placeholder template passed the guard"
    )


def test_bug_h_placeholder_guard_ignores_code_block_examples():
    """Meta skills (e.g. writing-skills/SKILL.md) contain bracket examples
    inside fenced code blocks — those must NOT count toward the density
    check, or we'd reject legitimate docs."""
    content = (
        "# Skill: Writing Skills\n\n"
        "Real content here — this skill teaches how to write skills.\n\n"
        "Example template (inside a code block — should be ignored by the guard):\n\n"
        "```markdown\n"
        "## Purpose\n"
        "[One sentence: what problem does this solve]\n"
        "[First step]\n"
        "[What NOT to do]\n"
        "[Another placeholder]\n"
        "```\n\n"
        "More real content after the example.\n"
    )
    assert _is_meaningful_skill_content(content), (
        "Bug H regression: code-block bracket examples incorrectly triggered the guard"
    )


def test_bug_h_is_stub_catches_placeholder_density(tmp_path: Path):
    """quality_checker.is_stub() must also flag bracketed-placeholder files
    so the reuse/adapt classification routes them to LLM regeneration."""
    from generator.utils.quality_checker import is_stub, is_stub_content

    stale = (
        "# Skill: Gemini API\n"
        "## Purpose\n"
        "[One sentence: what problem does this solve and for whom.]\n\n"
        "## When to use\n"
        "- [Scenario 1]\n"
        "- [Scenario 2]\n"
        "- [What NOT to do]\n"
    )

    # String-level guard
    assert is_stub_content(stale), (
        "Bug H regression: is_stub_content() missed placeholder-heavy stale file"
    )

    # File-level guard (what check_global_skill_reuse actually calls)
    stale_file = tmp_path / "gemini-api.md"
    stale_file.write_text(stale, encoding="utf-8")
    assert is_stub(stale_file), (
        "Bug H regression: is_stub() missed placeholder-heavy stale file on disk"
    )


def test_bug_c_create_skill_refuses_empty_content(tmp_path: Path, monkeypatch):
    """create_skill must raise ValueError rather than silently writing a
    junk skill file to global_learned."""
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

    generator = SkillGenerator(discovery)

    # Force the strategy chain to return junk
    monkeypatch.setattr(generator, "_run_strategy_chain", lambda *a, **kw: "content")

    with pytest.raises(ValueError, match="empty or missing a markdown heading"):
        generator.create_skill("real-skill-name")

    # And the skill dir must not linger as a hollow ghost
    assert not (discovery.global_learned / "real-skill-name").exists(), (
        "Bug C regression: empty skill dir was left behind after guard rejected content"
    )


def test_bug_c_sync_skips_blacklisted_names(tmp_path: Path, monkeypatch):
    """Test-named files in the builtin source must not be synced to
    ~/.project-rules-generator/builtin/ and thence into every project."""
    from generator.storage import skill_paths as sp

    src = tmp_path / "src_builtin"
    src.mkdir()
    # Legit skill — must be >= 80 bytes to clear the sync guard
    (src / "real-skill.md").write_text(
        "# Skill: Real\n\n## Purpose\n\nA real skill with plenty of meaningful "
        "content here so it clears the minimum-size guard.\n",
        encoding="utf-8",
    )
    # Blacklisted junk that previously leaked
    (src / "b.md").write_text("content", encoding="utf-8")
    (src / "conflict-skill.md").write_text("content", encoding="utf-8")
    (src / "test-skill.md").write_text("content", encoding="utf-8")

    target = tmp_path / "global_builtin"
    target.mkdir()

    monkeypatch.setattr(sp.SkillPathManager, "BUILTIN_SOURCE", src)
    monkeypatch.setattr(sp.SkillPathManager, "GLOBAL_BUILTIN", target)

    sp.SkillPathManager.sync_builtin_skills()

    assert (target / "real-skill.md").exists()
    assert not (target / "b.md").exists(), "Bug C regression: 'b.md' leaked through sync"
    assert not (target / "conflict-skill.md").exists(), (
        "Bug C regression: 'conflict-skill.md' leaked through sync"
    )
    assert not (target / "test-skill.md").exists(), (
        "Bug C regression: 'test-skill.md' leaked through sync"
    )

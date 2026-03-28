"""Tests for prg init and prg skills sub-commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.init_cmd import init
from cli.skills_cmd import skills_group


# ---------------------------------------------------------------------------
# prg init
# ---------------------------------------------------------------------------


class TestInitCommand:
    def test_init_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(init, ["--help"])
        assert result.exit_code == 0
        assert "First-run wizard" in result.output

    def test_init_creates_rules_md(self, tmp_path):
        (tmp_path / "README.md").write_text(
            "# My Project\nA Python project using FastAPI.", encoding="utf-8"
        )
        runner = CliRunner()
        with patch("generator.rules_generator.generate_rules", return_value="# Rules\n- rule 1"):
            result = runner.invoke(init, [str(tmp_path), "--yes"])
        assert result.exit_code == 0
        rules_file = tmp_path / ".clinerules" / "rules.md"
        assert rules_file.exists()

    def test_init_accepts_all_providers(self, tmp_path):
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        runner = CliRunner()
        for prov in ["gemini", "groq", "anthropic", "openai"]:
            with patch("generator.rules_generator.generate_rules", return_value="# Rules"):
                result = runner.invoke(init, [str(tmp_path), "--yes", "--provider", prov])
            assert "Error: Invalid value for '--provider'" not in result.output

    def test_init_rejects_unknown_provider(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(init, [str(tmp_path), "--provider", "badprovider"])
        assert result.exit_code != 0

    def test_init_works_without_readme(self, tmp_path):
        """Should fall back to structure-only mode when no README exists."""
        runner = CliRunner()
        with (
            patch("generator.rules_generator.generate_rules", return_value="# Rules"),
            patch("generator.project_analyzer.ProjectAnalyzer") as MockPA,
        ):
            MockPA.return_value.analyze.return_value = {"tech_stack": {"python": ["python"]}}
            result = runner.invoke(init, [str(tmp_path), "--yes"])
        # Should not crash — may warn but not error
        assert result.exit_code == 0

    def test_init_shows_next_steps(self, tmp_path):
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        runner = CliRunner()
        with patch("generator.rules_generator.generate_rules", return_value="# Rules"):
            result = runner.invoke(init, [str(tmp_path), "--yes"])
        assert "Next steps" in result.output

    def test_init_yes_flag_skips_confirm(self, tmp_path):
        """--yes should not prompt even when .clinerules already exists."""
        (tmp_path / ".clinerules").mkdir()
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        runner = CliRunner()
        with patch("generator.rules_generator.generate_rules", return_value="# Rules"):
            result = runner.invoke(init, [str(tmp_path), "--yes"])
        # Should not contain a prompt
        assert "Re-generate" not in result.output


# ---------------------------------------------------------------------------
# prg skills list
# ---------------------------------------------------------------------------


class TestSkillsListCommand:
    def test_skills_list_help(self):
        runner = CliRunner()
        result = runner.invoke(skills_group, ["list", "--help"])
        assert result.exit_code == 0
        assert "List all skills" in result.output

    def test_skills_list_shows_skills(self, tmp_path):
        """Creates a real skill file and verifies it appears in list output."""
        # Build minimal skill structure
        project_dir = tmp_path / ".clinerules" / "skills" / "project" / "my-skill"
        project_dir.mkdir(parents=True)
        (project_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ntriggers:\n  - do the thing\nallowed-tools: Bash\n---\n## Purpose\nTest.\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        with patch("generator.skill_discovery.SkillDiscovery.ensure_global_structure"):
            result = runner.invoke(skills_group, ["list", str(tmp_path)])

        assert result.exit_code == 0
        assert "my-skill" in result.output

    def test_skills_list_no_skills_message(self, tmp_path):
        runner = CliRunner()
        with patch("generator.skills_manager.SkillsManager.list_skills", return_value={}):
            result = runner.invoke(skills_group, ["list", str(tmp_path)])
        assert result.exit_code == 0
        # Either "No skills found" or "No project or learned skills"
        assert "No" in result.output


# ---------------------------------------------------------------------------
# prg skills validate
# ---------------------------------------------------------------------------


class TestSkillsValidateCommand:
    def test_validate_passes_for_good_skill(self, tmp_path):
        skill_dir = tmp_path / ".clinerules" / "skills" / "project" / "good-skill"
        skill_dir.mkdir(parents=True)
        good_content = (
            "---\nname: good-skill\ntriggers:\n  - fix bug\n  - debug code\n  - trace error\n"
            "allowed-tools: Bash Read\n---\n"
            "## Purpose\nDebug and fix issues.\n"
            "## Auto-Trigger\n**fix bug** **debug code** **trace error**\n"
            "## Process\n1. Step one\n2. Step two\n"
            "## Output\nFixed code.\n"
            "```bash\npython test.py\n```\n"
        )
        (skill_dir / "SKILL.md").write_text(good_content, encoding="utf-8")

        runner = CliRunner()
        skill_path = str(skill_dir / "SKILL.md")
        result = runner.invoke(skills_group, ["validate", skill_path, str(tmp_path)])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_validate_fails_for_stub_skill(self, tmp_path):
        skill_dir = tmp_path / ".clinerules" / "skills" / "project" / "bad-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "Follow project conventions\n[describe what this does]\n", encoding="utf-8"
        )

        runner = CliRunner()
        skill_path = str(skill_dir / "SKILL.md")
        result = runner.invoke(skills_group, ["validate", skill_path, str(tmp_path)])
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_validate_not_found_exits_1(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(skills_group, ["validate", "nonexistent-skill", str(tmp_path)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# prg skills show
# ---------------------------------------------------------------------------


class TestSkillsShowCommand:
    def test_show_displays_frontmatter(self, tmp_path):
        skill_dir = tmp_path / ".clinerules" / "skills" / "project" / "demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: A demo skill.\ntriggers:\n  - do demo\nallowed-tools: Bash\n---\n"
            "## Purpose\nDemonstrate things.\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        skill_path = str(skill_dir / "SKILL.md")
        result = runner.invoke(skills_group, ["show", skill_path, str(tmp_path)])
        assert result.exit_code == 0
        assert "demo-skill" in result.output
        assert "Frontmatter" in result.output
        assert "Body" in result.output

    def test_show_not_found_exits_1(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(skills_group, ["show", "ghost-skill", str(tmp_path)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

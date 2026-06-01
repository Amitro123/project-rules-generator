"""Tests for cli/analyze_helpers.py.

These helpers carry the branch logic of the core ``prg analyze`` command and were
at 33% coverage (CR §4.4). They split into:

- ``normalize_analyze_options`` — pure flag resolution (mode/provider → ai flags)
- ``_handle_skill_management`` — create/remove/list skill early-exits (raise Exit)
- ``_run_create_rules`` — the CoworkRulesCreator block (best-effort, swallows errors)
- ``setup_*`` helpers — thin wiring around collaborators
- ``commit_generated_files`` — git commit gating, incl. conventional-commit hook guard

Collaborators are mocked so no AI/network/git is required.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import click
import pytest

from cli.analyze_helpers import (
    _handle_skill_management,
    _run_create_rules,
    commit_generated_files,
    normalize_analyze_options,
    setup_incremental,
    setup_logging_and_provider,
    setup_orchestrator,
)

# ─── normalize_analyze_options ────────────────────────────────────────────────


class TestNormalizeAnalyzeOptions:
    def test_mode_ai_enables_skills_and_ai(self):
        skills, ai, const = normalize_analyze_options("ai", None, False, False, False)
        assert (skills, ai, const) == (True, True, False)

    def test_mode_constitution_enables_constitution(self):
        skills, ai, const = normalize_analyze_options("constitution", None, False, False, False)
        assert const is True
        assert ai is False

    def test_mode_manual_changes_nothing(self):
        skills, ai, const = normalize_analyze_options("manual", None, False, False, False)
        assert (skills, ai, const) == (False, False, False)

    def test_provider_implies_full_ai_intent(self):
        """An explicit provider (non-manual) turns on skills, ai, and constitution."""
        skills, ai, const = normalize_analyze_options(None, "groq", False, False, False)
        assert (skills, ai, const) == (True, True, True)

    def test_manual_mode_overrides_provider(self):
        """--mode manual suppresses provider-implied AI intent."""
        skills, ai, const = normalize_analyze_options("manual", "groq", False, False, False)
        assert (skills, ai, const) == (False, False, False)

    def test_bare_ai_flag_enables_skill_generation(self):
        """Bug A: --ai alone (no provider) must still enable skill generation."""
        skills, ai, const = normalize_analyze_options(None, None, False, True, False)
        assert skills is True
        assert ai is True


# ─── _handle_skill_management ─────────────────────────────────────────────────


def _make_manager(tmp_path):
    mgr = MagicMock()
    mgr.project_path = tmp_path
    mgr.learned_path = tmp_path / "learned"
    mgr.learned_path.mkdir(exist_ok=True)
    return mgr


def _call_skill_mgmt(mgr, **overrides):
    """Invoke _handle_skill_management with sensible defaults."""
    kwargs = dict(
        skills_manager=mgr,
        create_skill=None,
        add_skill=None,
        from_readme=None,
        ai=False,
        provider=None,
        force=False,
        strategy=None,
        output_dir=mgr.project_path,
        create_rules_flag=False,
        remove_skill=None,
        list_skills=False,
        verbose=False,
        scope="learned",
    )
    kwargs.update(overrides)
    return _handle_skill_management(**kwargs)


class TestHandleSkillManagement:
    def test_create_skill_exits_zero_when_no_rules_follow(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_skill.return_value = tmp_path / "myskill"
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, create_skill="myskill")
        assert exc.value.exit_code == 0
        mgr.create_skill.assert_called_once()
        mgr.save_triggers_json.assert_called_once()

    def test_create_skill_continues_when_rules_flag_set(self, tmp_path):
        """With --create-rules also set, creation does NOT early-exit."""
        mgr = _make_manager(tmp_path)
        mgr.create_skill.return_value = tmp_path / "myskill"
        # No Exit raised → function returns None and the analyze flow continues.
        assert _call_skill_mgmt(mgr, create_skill="myskill", create_rules_flag=True) is None

    def test_create_skill_failure_exits_one(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_skill.side_effect = RuntimeError("boom")
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, create_skill="bad")
        assert exc.value.exit_code == 1

    def test_remove_skill_outside_learned_rejected(self, tmp_path):
        """A traversal path that escapes learned_path is rejected with Exit 1."""
        mgr = _make_manager(tmp_path)
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, remove_skill="../escape")
        assert exc.value.exit_code == 1

    def test_remove_skill_missing_exits_one(self, tmp_path):
        mgr = _make_manager(tmp_path)
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, remove_skill="ghost")
        assert exc.value.exit_code == 1

    def test_remove_skill_success_exits_zero(self, tmp_path):
        mgr = _make_manager(tmp_path)
        target = mgr.learned_path / "old"
        target.mkdir()
        (target / "SKILL.md").write_text("x")
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, remove_skill="old")
        assert exc.value.exit_code == 0
        assert not target.exists()
        mgr.generate_perfect_index.assert_called_once()

    def test_remove_skill_tolerates_refresh_failures(self, tmp_path, capsys):
        """Index/triggers refresh failures after removal are non-fatal warnings."""
        mgr = _make_manager(tmp_path)
        target = mgr.learned_path / "old"
        target.mkdir()
        mgr.generate_perfect_index.side_effect = RuntimeError("index broke")
        mgr.save_triggers_json.side_effect = RuntimeError("triggers broke")
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, remove_skill="old")
        assert exc.value.exit_code == 0
        err = capsys.readouterr().err
        assert "Could not refresh index.md" in err
        assert "Could not refresh auto-triggers.json" in err

    def test_list_skills_groups_and_exits_zero(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.list_skills.return_value = {
            "p1": {"type": "project"},
            "l1": {"type": "learned"},
            "b1": {"type": "builtin"},
        }
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, list_skills=True)
        assert exc.value.exit_code == 0

    def test_list_skills_empty_exits_zero(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.list_skills.return_value = {}
        with pytest.raises(click.exceptions.Exit) as exc:
            _call_skill_mgmt(mgr, list_skills=True)
        assert exc.value.exit_code == 0

    def test_no_action_returns_none(self, tmp_path):
        """When no skill action flags are set, the helper is a no-op."""
        mgr = _make_manager(tmp_path)
        assert _call_skill_mgmt(mgr) is None


# ─── _run_create_rules ────────────────────────────────────────────────────────


class TestRunCreateRules:
    def _quality(self, score):
        return SimpleNamespace(score=score)

    def test_generates_and_appends_file(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Proj\n\nDoes things.")
        generated = []
        metadata = SimpleNamespace(tech_stack=["python"], project_type="cli")

        with patch("generator.rules.CoworkRulesCreator") as creator_cls:
            creator = creator_cls.return_value
            creator.create_rules.return_value = ("RULES", metadata, self._quality(95.0))
            creator.export_to_file.return_value = tmp_path / "rules.md"

            _run_create_rules(
                tmp_path,
                readme,
                "Proj",
                {"tech_stack": ["python"]},
                {},
                tmp_path,
                85,
                True,
                generated,
            )

        assert (tmp_path / "rules.md") in generated

    def test_low_quality_warns_but_still_writes(self, tmp_path, capsys):
        readme = tmp_path / "README.md"
        readme.write_text("# Proj")
        generated = []
        metadata = SimpleNamespace(tech_stack=[], project_type="unknown")

        with patch("generator.rules.CoworkRulesCreator") as creator_cls:
            creator = creator_cls.return_value
            creator.create_rules.return_value = ("RULES", metadata, self._quality(40.0))
            creator.export_to_file.return_value = tmp_path / "rules.md"
            _run_create_rules(
                tmp_path,
                readme,
                "Proj",
                {},
                {},
                tmp_path,
                85,
                False,
                generated,
            )

        assert (tmp_path / "rules.md") in generated
        assert "below threshold" in capsys.readouterr().err

    def test_missing_readme_uses_placeholder(self, tmp_path):
        """No README on disk → a placeholder body is synthesised, not a crash."""
        generated = []
        metadata = SimpleNamespace(tech_stack=[], project_type="x")
        with patch("generator.rules.CoworkRulesCreator") as creator_cls:
            creator = creator_cls.return_value
            creator.create_rules.return_value = ("R", metadata, self._quality(90))
            creator.export_to_file.return_value = tmp_path / "rules.md"
            _run_create_rules(
                tmp_path,
                tmp_path / "missing.md",
                "Proj",
                {},
                {},
                tmp_path,
                85,
                False,
                generated,
            )
        readme_arg = creator.create_rules.call_args.args[0]
        assert "Project analysis in progress" in readme_arg

    def test_creator_exception_is_swallowed(self, tmp_path, capsys):
        """A failure in rules generation is reported, not raised (CLI boundary)."""
        generated = []
        with patch("generator.rules.CoworkRulesCreator") as creator_cls:
            creator_cls.return_value.create_rules.side_effect = RuntimeError("kaboom")
            _run_create_rules(
                tmp_path,
                None,
                "Proj",
                {},
                {},
                tmp_path,
                85,
                True,
                generated,
            )
        assert generated == []
        assert "Cowork rules generation failed" in capsys.readouterr().err


# ─── setup_* helpers ──────────────────────────────────────────────────────────


class TestSetupHelpers:
    def test_setup_orchestrator_registers_two_sources(self):
        with (
            patch("generator.skills.orchestrator.SkillOrchestrator") as orch_cls,
            patch("generator.sources.builtin.BuiltinSkillsSource"),
            patch("generator.sources.learned.LearnedSkillsSource"),
        ):
            result = setup_orchestrator(config={})
        assert result is orch_cls.return_value
        assert orch_cls.return_value.register_source.call_count == 2

    def test_setup_logging_and_provider_returns_resolved(self):
        with (
            patch("cli.utils.detect_provider", return_value="gemini"),
            patch("cli.utils.set_api_key_env") as set_key,
            patch("prg_utils.logger.setup_logging"),
        ):
            resolved = setup_logging_and_provider(True, None, "key123", "9.9")
        assert resolved == "gemini"
        set_key.assert_called_once_with("gemini", "key123")

    def test_setup_logging_handles_no_provider(self):
        with (
            patch("cli.utils.detect_provider", return_value=None),
            patch("cli.utils.set_api_key_env"),
            patch("prg_utils.logger.setup_logging"),
        ):
            resolved = setup_logging_and_provider(False, None, None, "9.9")
        assert resolved == ""

    def test_setup_incremental_returns_none_when_disabled(self, tmp_path):
        assert setup_incremental(False, tmp_path, tmp_path) is None

    def test_setup_incremental_exits_when_no_changes(self, tmp_path):
        with patch("generator.analyzers.incremental_analyzer.IncrementalAnalyzer") as inc_cls:
            inc_cls.return_value.detect_changes.return_value = []
            with pytest.raises(SystemExit) as exc:
                setup_incremental(True, tmp_path, tmp_path)
            assert exc.value.code == 0

    def test_setup_incremental_returns_analyzer_when_changes(self, tmp_path):
        with patch("generator.analyzers.incremental_analyzer.IncrementalAnalyzer") as inc_cls:
            inc_cls.return_value.detect_changes.return_value = ["section_a"]
            result = setup_incremental(True, tmp_path, tmp_path)
        assert result is inc_cls.return_value


# ─── commit_generated_files ───────────────────────────────────────────────────


class TestCommitGeneratedFiles:
    def test_noop_when_commit_false(self, tmp_path):
        with patch("prg_utils.git_ops.is_git_repo") as is_repo:
            commit_generated_files(False, {}, [], tmp_path, interactive=False)
        is_repo.assert_not_called()

    def test_warns_when_not_git_repo(self, tmp_path, capsys):
        with patch("prg_utils.git_ops.is_git_repo", return_value=False):
            commit_generated_files(True, {}, ["a.md"], tmp_path, interactive=False)
        assert "Not a git repository" in capsys.readouterr().out

    def test_non_git_repo_quiet_in_interactive(self, tmp_path, capsys):
        with patch("prg_utils.git_ops.is_git_repo", return_value=False):
            commit_generated_files(True, {}, ["a.md"], tmp_path, interactive=True)
        assert "Not a git repository" not in capsys.readouterr().out

    def test_successful_commit(self, tmp_path, capsys):
        with (
            patch("prg_utils.git_ops.is_git_repo", return_value=True),
            patch("prg_utils.git_ops.commit_files", return_value="1 file changed") as cf,
        ):
            commit_generated_files(True, {}, ["a.md"], tmp_path, interactive=False)
        cf.assert_called_once()
        assert "Committed to git" in capsys.readouterr().out

    def test_conventional_commit_hook_blocks_bad_message(self, tmp_path, capsys):
        """A commit-msg hook enforcing conventional commits + a non-conforming
        configured message → the auto-commit is skipped with guidance."""
        hooks = tmp_path / ".git" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "commit-msg").write_text("# enforces conventional commits: feat|fix etc")
        config = {"git": {"commit_message": "just some words"}}

        with (
            patch("prg_utils.git_ops.is_git_repo", return_value=True),
            patch("prg_utils.git_ops.commit_files") as cf,
        ):
            commit_generated_files(True, config, ["a.md"], tmp_path, interactive=False)

        cf.assert_not_called()
        assert "Skipping auto-commit" in capsys.readouterr().out

    def test_conventional_commit_hook_allows_good_message(self, tmp_path):
        """A conforming conventional message passes the hook guard and commits."""
        hooks = tmp_path / ".git" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "commit-msg").write_text("# enforces conventional commits: feat|fix")
        config = {"git": {"commit_message": "chore: regenerate rules"}}

        with (
            patch("prg_utils.git_ops.is_git_repo", return_value=True),
            patch("prg_utils.git_ops.commit_files", return_value="ok") as cf,
        ):
            commit_generated_files(True, config, ["a.md"], tmp_path, interactive=False)
        cf.assert_called_once()

    def test_successful_commit_reports_nothing_to_commit(self, tmp_path, capsys):
        """A 'nothing to commit' result adds the already-tracked hint."""
        with (
            patch("prg_utils.git_ops.is_git_repo", return_value=True),
            patch("prg_utils.git_ops.commit_files", return_value="nothing to commit, working tree clean"),
        ):
            commit_generated_files(True, {}, ["a.md"], tmp_path, interactive=False)
        out = capsys.readouterr().out
        assert "already tracked" in out

    def test_unreadable_hook_falls_through_to_commit(self, tmp_path):
        """If reading the commit-msg hook raises OSError, the guard is skipped
        and the commit proceeds (the OSError is swallowed)."""
        hooks = tmp_path / ".git" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "commit-msg").write_text("# conventional commits enforced")
        config = {"git": {"commit_message": "anything at all"}}

        with (
            patch("prg_utils.git_ops.is_git_repo", return_value=True),
            patch("prg_utils.git_ops.commit_files", return_value="ok") as cf,
            patch("pathlib.Path.read_text", side_effect=OSError("permission denied")),
        ):
            commit_generated_files(True, config, ["a.md"], tmp_path, interactive=False)
        cf.assert_called_once()

    def test_commit_failure_is_reported(self, tmp_path, capsys):
        with (
            patch("prg_utils.git_ops.is_git_repo", return_value=True),
            patch("prg_utils.git_ops.commit_files", side_effect=RuntimeError("git locked")),
        ):
            commit_generated_files(True, {}, ["a.md"], tmp_path, interactive=False)
        assert "Git commit failed" in capsys.readouterr().out

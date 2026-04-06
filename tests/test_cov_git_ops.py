"""Coverage boost: prg_utils.git_ops (43% covered, 43 miss)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prg_utils.git_ops import (
    _posix,
    commit_changes,
    commit_files,
    create_branch,
    default_branch,
    delete_branch,
    get_current_branch,
    has_staged_changes,
    is_git_repo,
    stage_files,
)


class TestPosix:
    def test_converts_windows_path(self):
        result = _posix(Path("C:/Users/dana/project"))
        assert "\\" not in result

    def test_string_path_unchanged_posix(self):
        result = _posix("/home/user/project")
        assert result == "/home/user/project"


class TestIsGitRepo:
    def test_returns_true_for_valid_repo(self, tmp_path):
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            assert is_git_repo(tmp_path) is True

    def test_returns_false_when_called_process_error(self, tmp_path):
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(128, "git")):
            assert is_git_repo(tmp_path) is False

    def test_returns_false_when_git_not_found(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError("no git")):
            assert is_git_repo(tmp_path) is False


class TestStageFiles:
    def test_stages_successfully(self, tmp_path):
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            stage_files(["file.py"], tmp_path)

    def test_gitignored_file_prints_message(self, tmp_path, capsys):
        import subprocess

        err = subprocess.CalledProcessError(1, "git")
        err.stderr = "The following paths are ignored by git"
        with patch("subprocess.run", side_effect=err):
            stage_files(["ignored.py"], tmp_path)
        captured = capsys.readouterr()
        assert "IGNORED" in captured.out

    def test_real_error_is_raised(self, tmp_path):
        import subprocess

        err = subprocess.CalledProcessError(1, "git")
        err.stderr = "fatal: not a repository"
        with patch("subprocess.run", side_effect=err):
            with pytest.raises(subprocess.CalledProcessError):
                stage_files(["file.py"], tmp_path)


class TestCommitChanges:
    def test_returns_stdout_on_success(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="[main abc123] My commit\n")
        with patch("subprocess.run", return_value=mock_result):
            result = commit_changes("My commit", tmp_path)
        assert "abc123" in result

    def test_returns_nothing_to_commit_message(self, tmp_path):
        mock_result = MagicMock(returncode=1, stdout="nothing to commit", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = commit_changes("test", tmp_path)
        assert result == "Nothing to commit"

    def test_raises_on_failure(self, tmp_path):
        mock_result = MagicMock(returncode=1, stdout="", stderr="fatal: bad object")
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Git commit failed"):
                commit_changes("msg", tmp_path)

    def test_sets_env_when_user_provided(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="ok")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            commit_changes("msg", tmp_path, user_name="Alice", user_email="alice@example.com")
        call_kwargs = mock_run.call_args
        env = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env")
        assert env is not None
        assert env.get("GIT_AUTHOR_NAME") == "Alice"


class TestHasStagedChanges:
    def test_returns_true_when_changes_staged(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert has_staged_changes(tmp_path) is True

    def test_returns_false_when_nothing_staged(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            assert has_staged_changes(tmp_path) is False


class TestCommitFiles:
    def test_raises_when_not_git_repo(self, tmp_path):
        with patch("prg_utils.git_ops.is_git_repo", return_value=False):
            with pytest.raises(RuntimeError, match="Not a git repository"):
                commit_files(["file.py"], "msg", tmp_path)

    def test_returns_nothing_to_commit_when_no_staged(self, tmp_path):
        with patch("prg_utils.git_ops.is_git_repo", return_value=True):
            with patch("prg_utils.git_ops.stage_files"):
                with patch("prg_utils.git_ops.has_staged_changes", return_value=False):
                    result = commit_files(["file.py"], "msg", tmp_path)
        assert result == "Nothing to commit"

    def test_commits_when_staged(self, tmp_path):
        with patch("prg_utils.git_ops.is_git_repo", return_value=True):
            with patch("prg_utils.git_ops.stage_files"):
                with patch("prg_utils.git_ops.has_staged_changes", return_value=True):
                    with patch("prg_utils.git_ops.commit_changes", return_value="committed"):
                        result = commit_files(["file.py"], "msg", tmp_path)
        assert result == "committed"


class TestDefaultBranch:
    def test_returns_main_from_remote_head(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="origin/main\n")
        with patch("subprocess.run", return_value=mock_result):
            result = default_branch(tmp_path)
        assert result == "main"

    def test_falls_back_to_local_main(self, tmp_path):
        side_effects = [
            MagicMock(returncode=1, stdout=""),  # remote HEAD fails
            MagicMock(returncode=0, stdout=""),  # local main exists
        ]
        with patch("subprocess.run", side_effect=side_effects):
            result = default_branch(tmp_path)
        assert result == "main"

    def test_falls_back_to_master_when_main_missing(self, tmp_path):
        side_effects = [
            MagicMock(returncode=1, stdout=""),  # remote HEAD fails
            MagicMock(returncode=1, stdout=""),  # main not found
            MagicMock(returncode=0, stdout=""),  # master found
        ]
        with patch("subprocess.run", side_effect=side_effects):
            result = default_branch(tmp_path)
        assert result == "master"

    def test_returns_main_when_nothing_found(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="")):
            result = default_branch(tmp_path)
        assert result == "main"

    def test_handles_file_not_found_for_remote(self, tmp_path):
        side_effects = [
            FileNotFoundError("git not found"),
            MagicMock(returncode=0, stdout=""),  # local main found
        ]
        with patch("subprocess.run", side_effect=side_effects):
            result = default_branch(tmp_path)
        assert result == "main"


class TestGetCurrentBranch:
    def test_returns_branch_name(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="feature-x\n")):
            result = get_current_branch(tmp_path)
        assert result == "feature-x"


class TestCreateBranch:
    def test_calls_git_checkout_b(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            create_branch("new-branch", tmp_path)
        args = mock_run.call_args[0][0]
        assert "checkout" in args
        assert "-b" in args
        assert "new-branch" in args


class TestDeleteBranch:
    def test_uses_d_flag_by_default(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            delete_branch("old-branch", force=False, repo_path=tmp_path)
        args = mock_run.call_args[0][0]
        assert "-d" in args

    def test_uses_D_flag_when_forced(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            delete_branch("old-branch", force=True, repo_path=tmp_path)
        args = mock_run.call_args[0][0]
        assert "-D" in args

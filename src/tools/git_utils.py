"""Git operations utility module."""

import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


def _posix(path: Union[str, Path]) -> str:
    """Convert path to forward-slash format for git compatibility on Windows."""
    return Path(path).as_posix()


def is_git_repo(path: Union[str, Path]) -> bool:
    """Check if path is a git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", _posix(path), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def stage_files(paths: List[Union[str, Path]], repo_path: Union[str, Path] = ".") -> None:
    """Stage files for commit."""
    repo = _posix(repo_path)
    for path in paths:
        try:
            subprocess.run(
                ["git", "-C", repo, "add", _posix(path)],
                capture_output=True,
                check=True,
                text=True,
            )
        except FileNotFoundError as fe:
            raise RuntimeError("git executable not found. Please install Git or ensure it is on PATH.") from fe
        except subprocess.CalledProcessError as e:
            # Check if failure is due to .gitignore
            # git usually returns 1 and prints "The following paths are ignored..." to stderr
            msg = f"{(e.stderr or '')}{(e.stdout or '')}"
            if "ignored" in msg.lower():
                logger.info("[IGNORED] Files generated successfully (ignored by .gitignore): %s", path)
                continue
            # Re-raise real errors
            raise e


def commit_changes(
    message: str,
    repo_path: Union[str, Path] = ".",
    user_name: Optional[str] = None,
    user_email: Optional[str] = None,
) -> str:
    """Commit staged changes.

    Returns:
        - str: Commit output on success
        - "Nothing to commit" if there are no staged changes to commit
    """
    env = {}
    if user_name:
        env["GIT_AUTHOR_NAME"] = user_name
        env["GIT_COMMITTER_NAME"] = user_name
    if user_email:
        env["GIT_AUTHOR_EMAIL"] = user_email
        env["GIT_COMMITTER_EMAIL"] = user_email

    try:
        result = subprocess.run(
            ["git", "-C", _posix(repo_path), "commit", "-m", message],
            capture_output=True,
            text=True,
            env={**os.environ, **env} if env else None,
        )
    except FileNotFoundError as fe:
        raise RuntimeError("git executable not found. Please install Git or ensure it is on PATH.") from fe

    if result.returncode != 0:
        if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
            return "Nothing to commit"
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        raise RuntimeError(f"Git commit failed. stdout: {out} stderr: {err}")

    return result.stdout.strip()


def commit_files(
    paths: List[Union[str, Path]],
    message: str,
    repo_path: Union[str, Path] = ".",
    user_name: Optional[str] = None,
    user_email: Optional[str] = None,
) -> str:
    """Stage and commit files in one operation."""
    if not is_git_repo(repo_path):
        raise RuntimeError(f"Not a git repository: {repo_path}")

    stage_files(paths, repo_path)
    return commit_changes(message, repo_path, user_name, user_email)


def create_branch(name: str, repo_path: Union[str, Path] = ".") -> None:
    """Create a new git branch."""
    subprocess.run(
        ["git", "-C", _posix(repo_path), "checkout", "-b", name],
        capture_output=True,
        check=True,
        text=True,
    )


def checkout(name: str, repo_path: Union[str, Path] = ".") -> None:
    """Checkout a branch."""
    subprocess.run(
        ["git", "-C", _posix(repo_path), "checkout", name],
        capture_output=True,
        check=True,
        text=True,
    )


def merge_branch(name: str, repo_path: Union[str, Path] = ".") -> None:
    """Merge a branch into the current one."""
    subprocess.run(
        ["git", "-C", _posix(repo_path), "merge", name],
        capture_output=True,
        check=True,
        text=True,
    )


def delete_branch(name: str, force: bool = False, repo_path: Union[str, Path] = ".") -> None:
    """Delete a branch."""
    flag = "-D" if force else "-d"
    subprocess.run(
        ["git", "-C", _posix(repo_path), "branch", flag, name],
        capture_output=True,
        check=True,
        text=True,
    )


def rollback_to_head(repo_path: Union[str, Path] = ".") -> None:
    """Hard reset to HEAD and clean untracked files."""
    repo = _posix(repo_path)
    subprocess.run(
        ["git", "-C", repo, "reset", "--hard", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", repo, "clean", "-fd"],
        capture_output=True,
        check=True,
        text=True,
    )


def get_current_branch(repo_path: Union[str, Path] = ".") -> str:
    """Get the name of the current branch."""
    result = subprocess.run(
        ["git", "-C", _posix(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.strip()

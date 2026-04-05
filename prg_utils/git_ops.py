"""Git operations utility module."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Union


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
        except subprocess.CalledProcessError as e:
            # Check if failure is due to .gitignore
            # git usually returns 1 and prints "The following paths are ignored..." to stderr
            if "paths are ignored by" in e.stderr:
                print(f"[IGNORED] Files generated successfully (ignored by .gitignore): {path}")
                continue
            # Re-raise real errors
            raise e


def commit_changes(
    message: str,
    repo_path: Union[str, Path] = ".",
    user_name: Optional[str] = None,
    user_email: Optional[str] = None,
) -> str:
    """Commit staged changes."""
    env = {}
    if user_name:
        env["GIT_AUTHOR_NAME"] = user_name
        env["GIT_COMMITTER_NAME"] = user_name
    if user_email:
        env["GIT_AUTHOR_EMAIL"] = user_email
        env["GIT_COMMITTER_EMAIL"] = user_email

    result = subprocess.run(
        ["git", "-C", _posix(repo_path), "commit", "-m", message],
        capture_output=True,
        text=True,
        env={**os.environ, **env} if env else None,
    )

    if result.returncode != 0:
        if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
            return "Nothing to commit"
        raise RuntimeError(f"Git commit failed: {result.stderr}")

    return result.stdout.strip()


def has_staged_changes(repo_path: Union[str, Path] = ".") -> bool:
    """Return True when the index has staged changes ready to commit."""
    result = subprocess.run(
        ["git", "-C", _posix(repo_path), "diff", "--cached", "--quiet"],
        capture_output=True,
    )
    # exit 0 = nothing staged, exit 1 = changes staged
    return result.returncode != 0


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

    if not has_staged_changes(repo_path):
        return "Nothing to commit"

    return commit_changes(message, repo_path, user_name, user_email)


def create_branch(name: str, repo_path: Union[str, Path] = ".") -> None:
    """Create a new git branch."""
    subprocess.run(
        ["git", "-C", _posix(repo_path), "checkout", "-b", name],
        capture_output=True,
        check=True,
        text=True,
    )


def default_branch(repo_path: Union[str, Path] = ".") -> str:
    """Return the default branch name (main or master) for the given repo.

    Tries the remote HEAD pointer first, then falls back to checking whether
    'main' or 'master' exist as local refs.  Returns 'main' if neither is found.
    """
    # Prefer the remote's HEAD pointer (most reliable)
    try:
        result = subprocess.run(
            ["git", "-C", _posix(repo_path), "rev-parse", "--abbrev-ref", "origin/HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            ref = result.stdout.strip()  # e.g. "origin/main"
            if "/" in ref:
                return ref.split("/", 1)[1]
    except FileNotFoundError:
        pass

    # Fall back to checking local branch refs
    for candidate in ("main", "master"):
        result = subprocess.run(
            ["git", "-C", _posix(repo_path), "rev-parse", "--verify", candidate],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return candidate
    return "main"


def checkout(name: str, repo_path: Union[str, Path] = ".") -> None:
    """Checkout a branch."""
    subprocess.run(
        ["git", "-C", _posix(repo_path), "checkout", name],
        capture_output=True,
        check=True,
        text=True,
    )


def merge_branch(name: str, repo_path: Union[str, Path] = ".") -> None:
    """Merge a branch into the current one (always creates a merge commit)."""
    subprocess.run(
        ["git", "-C", _posix(repo_path), "merge", "--no-ff", name],
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

"""Git operations utility module."""
import subprocess
from pathlib import Path
from typing import List, Union


def is_git_repo(path: Union[str, Path]) -> bool:
    """Check if path is a git repository."""
    try:
        result = subprocess.run(
            ['git', '-C', str(path), 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def stage_files(paths: List[Union[str, Path]], repo_path: Union[str, Path] = '.') -> None:
    """Stage files for commit."""
    for path in paths:
        subprocess.run(
            ['git', '-C', str(repo_path), 'add', str(path)],
            capture_output=True,
            check=True
        )


def commit_changes(message: str, repo_path: Union[str, Path] = '.', 
                   user_name: str = None, user_email: str = None) -> str:
    """Commit staged changes."""
    env = {}
    if user_name:
        env['GIT_AUTHOR_NAME'] = user_name
        env['GIT_COMMITTER_NAME'] = user_name
    if user_email:
        env['GIT_AUTHOR_EMAIL'] = user_email
        env['GIT_COMMITTER_EMAIL'] = user_email
    
    result = subprocess.run(
        ['git', '-C', str(repo_path), 'commit', '-m', message],
        capture_output=True,
        text=True,
        env={**subprocess.os.environ, **env} if env else None
    )
    
    if result.returncode != 0:
        if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
            return "Nothing to commit"
        raise RuntimeError(f"Git commit failed: {result.stderr}")
    
    return result.stdout.strip()


def commit_files(paths: List[Union[str, Path]], message: str, 
                 repo_path: Union[str, Path] = '.',
                 user_name: str = None, user_email: str = None) -> str:
    """Stage and commit files in one operation."""
    if not is_git_repo(repo_path):
        raise RuntimeError(f"Not a git repository: {repo_path}")
    
    stage_files(paths, repo_path)
    return commit_changes(message, repo_path, user_name, user_email)

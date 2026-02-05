"""File operations utility module."""
from pathlib import Path
from typing import Union


def read_file(path: Union[str, Path]) -> str:
    """Read file contents as text."""
    return Path(path).read_text(encoding='utf-8')


def save_markdown(path: Union[str, Path], content: str) -> None:
    """Save markdown content to file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def file_exists(path: Union[str, Path]) -> bool:
    """Check if file exists."""
    return Path(path).exists()


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if not."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

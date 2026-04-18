"""File operations utility module."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


def read_file(path: Union[str, Path]) -> str:
    """Read file contents as text."""
    return Path(path).read_text(encoding="utf-8")


def atomic_write_text(
    path: Union[str, Path],
    content: str,
    *,
    backup: bool = False,
    backup_suffix: str = ".bak",
) -> Optional[Path]:
    """Write ``content`` to ``path`` atomically.

    The content is first written to a temp file in the same directory, fsynced,
    then renamed into place with ``os.replace`` — which is atomic on POSIX and
    on Windows (when source and destination are on the same filesystem). This
    prevents a half-written file if the process is killed mid-write, and on
    POSIX guarantees readers never see a partial update.

    When ``backup`` is True and ``path`` already exists, the existing file is
    copied to ``path + backup_suffix`` *before* the replace. Returns the backup
    path (or ``None`` if no backup was made). The backup is overwritten on each
    subsequent write, so only the most recent prior revision is retained.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    backup_path: Optional[Path] = None
    if backup and path.exists():
        backup_path = path.with_name(path.name + backup_suffix)
        try:
            backup_path.write_bytes(path.read_bytes())
        except OSError as exc:
            logger.warning("Could not create backup %s: %s", backup_path, exc)
            backup_path = None

    # Write to a temp file in the same directory so os.replace stays on the
    # same filesystem (cross-device renames are not atomic).
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                # fsync can fail on some virtualised filesystems; not fatal.
                pass
        os.replace(tmp_path, path)
    except Exception:
        # Clean up the temp file if we failed before rename.
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise

    return backup_path


def save_markdown(path: Union[str, Path], content: str, *, backup: bool = False) -> None:
    """Save markdown content to file atomically.

    When ``backup`` is True and the destination already exists, the prior
    contents are preserved at ``<path>.bak`` before the overwrite. Callers
    that overwrite user-visible artifacts (e.g. ``rules.md``) should pass
    ``backup=True`` so a single re-run cannot destroy hand edits without
    leaving a recoverable copy.
    """
    atomic_write_text(path, content, backup=backup)


def file_exists(path: Union[str, Path]) -> bool:
    """Check if file exists."""
    return Path(path).exists()


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if not."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

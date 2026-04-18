"""Skill usage tracker — persists match counts and feedback scores to JSON."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

# Minimum feedback events before a skill can be flagged as low-scoring.
MIN_FEEDBACK_FOR_FLAG = 3

_DATA_DIR = Path.home() / ".project-rules-generator"
_DEFAULT_PATH = _DATA_DIR / "skill-usage.json"


# ---------------------------------------------------------------------------
# Cross-process file lock (portable: fcntl on POSIX, msvcrt on Windows).
# ---------------------------------------------------------------------------


@contextmanager
def _file_lock(lock_path: Path, *, timeout: float = 5.0) -> Iterator[None]:
    """Acquire an exclusive lock on ``lock_path``; release on exit.

    Uses fcntl.flock on POSIX and msvcrt.locking on Windows. Blocks until the
    lock is available or ``timeout`` elapses. On failure the context still
    yields (best-effort: better to proceed unlocked than crash user commands
    over telemetry), but a warning is logged.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Open in append mode so the file is created if missing without truncating.
    try:
        fh = open(lock_path, "a+")  # noqa: SIM115 — released in finally
    except OSError as exc:
        logger.warning("Could not open lock file %s: %s — proceeding unlocked", lock_path, exc)
        yield
        return

    acquired = False
    deadline = time.monotonic() + timeout
    try:
        if sys.platform == "win32":
            import msvcrt  # type: ignore[import-not-found]

            while True:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(0.05)
        else:
            import fcntl  # type: ignore[import-not-found]

            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(0.05)

        if not acquired:
            logger.warning("Could not acquire lock on %s within %.1fs — proceeding unlocked", lock_path, timeout)

        yield
    finally:
        if acquired:
            try:
                if sys.platform == "win32":
                    import msvcrt  # type: ignore[import-not-found]

                    # Rewind to start of the byte we locked before unlocking.
                    try:
                        fh.seek(0)
                    except OSError:
                        pass
                    try:
                        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                else:
                    import fcntl  # type: ignore[import-not-found]

                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:  # noqa: BLE001 — unlock is best-effort
                pass
        try:
            fh.close()
        except OSError:
            pass


class SkillTracker:
    """Thread-safe, multi-process-safe skill usage tracker.

    Data is stored in ~/.project-rules-generator/skill-usage.json so it
    accumulates across projects and survives skill regeneration.

    Concurrency guarantees:

    * Within a single process: a ``threading.Lock`` serialises mutations.
    * Across processes: a sidecar ``.lock`` file is held exclusively for the
      duration of each read-modify-write sequence, and writes go to a temp
      file renamed into place atomically. Two concurrent ``prg agent``
      invocations cannot clobber each other or produce a torn JSON file.

    Schema per entry:
        {
          "match_count": int,       # times matched via prg agent
          "useful_count": int,      # positive feedback votes
          "not_useful_count": int,  # negative feedback votes
          "last_used": str | null,  # ISO-8601 UTC timestamp
          "score": float            # useful / (useful + not_useful), default 0.5
        }
    """

    def __init__(self, data_path: Optional[Path] = None):
        self._path = Path(data_path) if data_path else _DEFAULT_PATH
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        self._lock = threading.Lock()
        self._data: Dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_match(self, skill_name: str) -> None:
        """Increment the match counter for *skill_name* and update last_used."""
        with self._lock, _file_lock(self._lock_path):
            self._reload_from_disk()
            entry = self._entry(skill_name)
            entry["match_count"] += 1
            entry["last_used"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def record_feedback(self, skill_name: str, useful: bool) -> float:
        """Record a useful / not-useful vote and return the updated score."""
        with self._lock, _file_lock(self._lock_path):
            self._reload_from_disk()
            entry = self._entry(skill_name)
            if useful:
                entry["useful_count"] += 1
            else:
                entry["not_useful_count"] += 1
            entry["score"] = self._calc_score(entry)
            self._save()
            return entry["score"]

    def get_score(self, skill_name: str) -> float:
        """Return the current score for *skill_name* (default 0.5 when unknown)."""
        with self._lock:
            return self._data.get(skill_name, {}).get("score", 0.5)

    def get_stats(self, skill_name: str) -> dict:
        """Return the full stats dict for *skill_name* (empty dict if unknown)."""
        with self._lock:
            return dict(self._data.get(skill_name, {}))

    def get_low_scoring(self, threshold: float = 0.3) -> List[str]:
        """Return skill names whose score is below *threshold*.

        Requires at least MIN_FEEDBACK_FOR_FLAG votes to be flagged.
        """
        with self._lock:
            result = []
            for name, entry in self._data.items():
                total_feedback = entry.get("useful_count", 0) + entry.get("not_useful_count", 0)
                if total_feedback >= MIN_FEEDBACK_FOR_FLAG and entry.get("score", 0.5) < threshold:
                    result.append(name)
            return sorted(result)

    def all_stats(self) -> Dict[str, dict]:
        """Return a snapshot of all tracked skill stats."""
        with self._lock:
            return {k: dict(v) for k, v in self._data.items()}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _entry(self, skill_name: str) -> dict:
        """Return the mutable entry for *skill_name*, creating it if needed."""
        if skill_name not in self._data:
            self._data[skill_name] = {
                "match_count": 0,
                "useful_count": 0,
                "not_useful_count": 0,
                "last_used": None,
                "score": 0.5,
            }
        return self._data[skill_name]

    @staticmethod
    def _calc_score(entry: dict) -> float:
        total = entry.get("useful_count", 0) + entry.get("not_useful_count", 0)
        if total == 0:
            return 0.5
        return entry.get("useful_count", 0) / total

    def _load(self) -> None:
        """Initial load — no file lock (constructor path)."""
        self._data = self._read_from_disk()

    def _reload_from_disk(self) -> None:
        """Re-read the JSON file inside a held lock so concurrent writers
        from other processes don't get clobbered by our pending mutation."""
        self._data = self._read_from_disk()

    def _read_from_disk(self) -> Dict[str, dict]:
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            if not raw.strip():
                return {}
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (OSError, ValueError) as exc:
            logger.warning("Could not load skill usage data from %s: %s", self._path, exc)
            return {}

    def _save(self) -> None:
        """Atomic write via same-directory temp file + os.replace."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self._data, indent=2)
            tmp_path = self._path.with_suffix(self._path.suffix + f".tmp.{os.getpid()}")
            try:
                tmp_path.write_text(payload, encoding="utf-8")
                os.replace(tmp_path, self._path)
            except Exception:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
                raise
        except OSError as exc:
            logger.warning("Could not save skill usage data to %s: %s", self._path, exc)

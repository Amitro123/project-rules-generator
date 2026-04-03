"""Skill usage tracker — persists match counts and feedback scores to JSON."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Minimum feedback events before a skill can be flagged as low-scoring.
MIN_FEEDBACK_FOR_FLAG = 3

_DATA_DIR = Path.home() / ".project-rules-generator"
_DEFAULT_PATH = _DATA_DIR / "skill-usage.json"


class SkillTracker:
    """Thread-safe skill usage tracker backed by a JSON sidecar file.

    Data is stored in ~/.project-rules-generator/skill-usage.json so it
    accumulates across projects and survives skill regeneration.

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
        self._lock = threading.Lock()
        self._data: Dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_match(self, skill_name: str) -> None:
        """Increment the match counter for *skill_name* and update last_used."""
        with self._lock:
            entry = self._entry(skill_name)
            entry["match_count"] += 1
            entry["last_used"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def record_feedback(self, skill_name: str, useful: bool) -> float:
        """Record a useful / not-useful vote and return the updated score."""
        with self._lock:
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
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            self._data = json.loads(raw)
        except Exception as exc:
            logger.warning("Could not load skill usage data from %s: %s", self._path, exc)
            self._data = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not save skill usage data to %s: %s", self._path, exc)

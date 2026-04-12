"""FeatureState — persisted state model for a Ralph feature run (STATE.json)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FeatureState:
    """Persisted state for a single Ralph feature run (STATE.json)."""

    feature_id: str
    task: str
    branch_name: str
    status: str = "planning_complete"  # planning_complete|running|success|stopped|max_iterations
    iteration: int = 0
    tasks_total: int = 0
    tasks_complete: int = 0
    max_iterations: int = 20
    last_review_score: Optional[int] = None
    test_pass_rate: Optional[float] = None
    exit_condition: Optional[str] = None
    human_feedback: Optional[str] = None
    consecutive_test_failures: int = 0
    consecutive_agent_failures: int = 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, state_path: Path) -> "FeatureState":
        """Load state from STATE.json."""
        data = json.loads(state_path.read_text(encoding="utf-8"))
        # Only pass known fields to avoid TypeError on unknown keys
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def save(self, state_path: Path) -> None:
        """Persist state to STATE.json atomically (write-to-tmp then os.replace)."""
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        os.replace(tmp, state_path)

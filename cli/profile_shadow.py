"""Shadow-mode ProjectProfile validation.

Runs ``ProjectProfile.validate_invariants()`` and
``ProjectProfile.validate_against_disk()`` over the live pipeline output
WITHOUT failing the run. Violations are logged at WARNING level and
persisted to ``<output_dir>/.prg-invariants.json`` so the user can grep
for them after a run.

Purpose: surface contract violations in real usage before any producer is
migrated to write into ProjectProfile directly. The next refactor phases
move detection code behind the contract; once shadow runs are clean across
representative projects, the same checks can be promoted from log-only to
hard failures.

See: Plans/prg-systemic-bug-refactor.md (phase 1 → phase 2 transition).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from generator.project_profile import from_enhanced_context

logger = logging.getLogger(__name__)

INVARIANTS_REPORT_FILENAME = ".prg-invariants.json"


def shadow_validate(
    enhanced_context: Optional[Dict[str, Any]],
    project_path: Path,
    selected_skill_refs: Iterable[str],
    output_dir: Path,
    *,
    verbose: bool = False,
) -> List[str]:
    """Build a ProjectProfile from the live pipeline state, run every
    invariant, and persist the result.

    This function is OBSERVATIONAL — it never raises and never alters
    pipeline output. Its only side effects are:
      * writing ``<output_dir>/.prg-invariants.json``
      * logging via ``logging.getLogger(__name__)``

    Parameters
    ----------
    enhanced_context : output of ``EnhancedProjectParser.extract_full_context()``.
        ``None`` is tolerated (early-exit, write empty report).
    project_path : repo root being analyzed.
    selected_skill_refs : the live ``enhanced_selected_skills`` set/iterable.
    output_dir : the ``.clinerules`` directory where artifacts have just been
        written; the report file is written here too.
    verbose : if True, echo violation count to logger.info on every run.

    Returns
    -------
    List[str] : human-readable violation messages. Empty when the live
    pipeline state satisfies every contract invariant.
    """
    if enhanced_context is None:
        _write_report(output_dir, profile=None, violations=["enhanced_context_missing"])
        logger.warning("shadow_validate: enhanced_context is None, skipping checks")
        return ["enhanced_context_missing"]

    refs_list = sorted({str(r) for r in selected_skill_refs if r})

    try:
        profile = from_enhanced_context(
            enhanced_context=enhanced_context,
            project_path=project_path,
            selected_skill_refs=refs_list,
        )
    except (TypeError, ValueError, KeyError) as exc:
        # The adapter is meant to tolerate weird shapes, but if it ever
        # raises we surface that as a violation instead of crashing the
        # pipeline.
        msg = f"adapter_error: {type(exc).__name__}: {exc}"
        _write_report(output_dir, profile=None, violations=[msg])
        logger.warning("shadow_validate: adapter failed: %s", msg)
        return [msg]

    violations: List[str] = []
    violations.extend(profile.validate_invariants(strict=False))
    violations.extend(profile.validate_against_disk(output_dir, strict=False))

    _write_report(output_dir, profile=profile, violations=violations)

    if violations:
        logger.warning(
            "shadow_validate: %d invariant violation(s) for project %r — see %s",
            len(violations),
            profile.project_name,
            output_dir / INVARIANTS_REPORT_FILENAME,
        )
        for v in violations:
            logger.warning("  - %s", v)
    elif verbose:
        logger.info(
            "shadow_validate: clean for %r (%d skills, %d tech)",
            profile.project_name,
            len(profile.selected_skills),
            len(profile.tech_stack),
        )

    return violations


def _write_report(
    output_dir: Path,
    *,
    profile: Optional[Any],
    violations: List[str],
) -> None:
    """Persist the shadow report. Overwrites on every run (idempotent)."""
    report: Dict[str, Any] = {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "violations": violations,
    }
    if profile is not None:
        skills_by_scope = profile.skill_refs_by_scope()
        report["profile"] = {
            "project_name": profile.project_name,
            "project_path": str(profile.project_path),
            "project_type": profile.project_type,
            "confidence": profile.confidence,
            "tech_stack": [{"name": t.name, "source": t.source} for t in profile.tech_stack],
            "languages": list(profile.languages),
            "skills_by_scope": skills_by_scope,
            "skills_total": len(profile.selected_skills),
            "signals": {
                "has_tests": profile.has_tests,
                "has_docker": profile.has_docker,
                "has_ci": profile.has_ci,
            },
        }

    report_path = output_dir / INVARIANTS_REPORT_FILENAME
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=False, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        # Don't let a report-write failure break the pipeline.
        logger.warning("shadow_validate: failed to write %s: %s", report_path, exc)

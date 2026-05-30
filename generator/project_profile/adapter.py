"""ProjectProfile adapters — build a frozen ProjectProfile from legacy
enhanced_context dicts without modifying any upstream producer.

Phase 1 of the systemic-bug refactor: this adapter lets the rest of the
pipeline construct a ProjectProfile from the existing enhanced_context
output. Later phases migrate producers to write directly into the contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from generator.project_profile.constants import SKILL_SCOPES
from generator.project_profile.models import ProjectProfile, SkillRef, TechEntry


def from_enhanced_context(
    enhanced_context: Dict[str, Any],
    project_path: Path,
    selected_skill_refs: Optional[List[str]] = None,
) -> ProjectProfile:
    """Build a ProjectProfile from the existing pipeline's enhanced_context.

    Phase 1 adapter: does not modify any producer. Reads the same fields the
    current pipeline writes into and packages them into the immutable contract.
    Use this in tests and as a non-invasive integration point before
    Phase 2/3 migrate the producers.

    Parameters
    ----------
    enhanced_context : output of ``EnhancedProjectParser.extract_full_context()``
    project_path : absolute path to the project root
    selected_skill_refs : the set/list of refs like ``"project/foo"`` /
        ``"learned/bar"`` / ``"builtin/baz"`` that the pipeline computed via
        ``EnhancedSkillMatcher`` and ``_auto_generate_skills``. Pass ``None``
        if skill selection has not happened yet (e.g. mid-pipeline call sites).
    """
    metadata = enhanced_context.get("metadata", {}) or {}
    structure = enhanced_context.get("structure", {}) or {}

    project_name = metadata.get("project_name") or project_path.name
    project_type = metadata.get("project_type") or structure.get("type") or "unknown"

    tech_stack = _build_tech_entries(
        tech_names=list(metadata.get("tech_stack", []) or []),
        enhanced_context=enhanced_context,
    )

    selected_skills = _parse_skill_refs(selected_skill_refs or [])

    languages = tuple(sorted(metadata.get("languages", []) or []))
    has_tests = bool(metadata.get("has_tests", False))
    has_docker = bool(metadata.get("has_docker", False))
    has_ci = bool((project_path / ".github" / "workflows").exists() or (project_path / ".gitlab-ci.yml").exists())
    confidence = float(metadata.get("confidence", structure.get("confidence", 0.0)) or 0.0)

    return ProjectProfile(
        project_name=str(project_name),
        project_path=Path(project_path).resolve(),
        project_type=str(project_type),
        tech_stack=tech_stack,
        selected_skills=selected_skills,
        languages=languages,
        has_tests=has_tests,
        has_docker=has_docker,
        has_ci=has_ci,
        confidence=confidence,
    )


def _build_tech_entries(
    tech_names: List[str],
    enhanced_context: Dict[str, Any],
) -> Tuple[TechEntry, ...]:
    """Annotate each tech with the strongest evidence the pipeline supplies.

    Generic rule (no project-specific knowledge):
      * If the tech name (case-insensitive) appears in the parsed dependency
        names from requirements.txt / pyproject.toml / package.json — source
        is ``"dependency"``.
      * Otherwise — source is ``"inferred"``.

    Real per-tech evidence (e.g. "reflex was detected because rxconfig.py
    exists" or "docker was detected from Dockerfile") belongs upstream in the
    detectors themselves and will be threaded through in Phase 2. Hardcoding
    a tech→source map in the contract layer is exactly the
    producer/consumer-drift pattern this refactor is replacing — so we don't
    do it here.
    """
    deps = enhanced_context.get("dependencies", {}) or {}
    dep_name_pool: set = set()
    for kind in ("python", "node", "python_dev", "node_dev"):
        for d in deps.get(kind, []) or []:
            name = (d.get("name") if isinstance(d, dict) else None) or ""
            if name:
                dep_name_pool.add(str(name).lower())

    entries: List[TechEntry] = []
    seen: set = set()
    for raw_name in tech_names:
        name = str(raw_name).lower().strip()
        if not name or name in seen:
            continue
        seen.add(name)
        source = "dependency" if name in dep_name_pool else "inferred"
        entries.append(TechEntry(name=name, source=source))
    return tuple(entries)


def _parse_skill_refs(refs: List[str]) -> Tuple[SkillRef, ...]:
    """Parse pipeline refs like 'project/foo' or 'learned/fastapi/async-patterns'
    into canonical SkillRef tuples keyed by terminal name.

    Dedup happens here: a ref appearing twice yields one SkillRef.
    """
    seen: Dict[Tuple[str, str], SkillRef] = {}
    for raw in refs:
        if not raw:
            continue
        parts = str(raw).split("/")
        if len(parts) < 2:
            continue
        scope = parts[0]
        if scope not in SKILL_SCOPES:
            continue
        terminal = parts[-1]
        key = (scope, terminal)
        if key not in seen:
            seen[key] = SkillRef(scope=scope, name=terminal)
    # Stable order: by scope precedence, then alphabetical
    scope_order = {s: i for i, s in enumerate(SKILL_SCOPES)}
    return tuple(sorted(seen.values(), key=lambda sr: (scope_order.get(sr.scope, 99), sr.name)))

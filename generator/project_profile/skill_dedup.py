"""Canonical cross-scope skill-ref dedup.

Replaces three scattered dedup sites that each used a different key scheme
and were the documented source of nbug.md (pydantic-validation in two
scopes) + Bug-1 ordering drift:

  1. ``adapter._parse_skill_refs`` — dedupes (scope, terminal_name) for the
     contract. Does NOT apply cross-scope precedence (it lets the
     ProjectProfile invariant catch collisions as violations).
  2. cross-scope dedup in cli/skill_pipeline.py:_auto_generate_skills —
     drops learned/X when project/X exists.
  3. per-scope ``seen_*`` dedup in generator/outputs/clinerules_generator.py
     — dedupes terminal names within each scope as it iterates.

``dedupe_skill_refs`` below is the canonical, generic pass. The pipeline
uses it once and the writer trusts the result.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Tuple

from generator.project_profile.constants import SKILL_SCOPES


def dedupe_skill_refs(
    refs: Iterable[str],
    scope_precedence: Tuple[str, ...] = SKILL_SCOPES,
) -> FrozenSet[str]:
    """Canonical dedup of skill refs across the pipeline.

    At most one ref per terminal-name across all scopes. When the same
    terminal name appears in multiple scopes, ``scope_precedence``
    determines which wins (earlier in the tuple = higher precedence).
    Default precedence is ``SKILL_SCOPES`` = ``("project", "learned",
    "builtin")`` — a project-local skill specifically tailored for the
    repo beats a generic learned-library entry of the same name.

    When the same (scope, terminal_name) appears via different category
    prefixes (e.g. ``learned/fastapi/async-patterns`` and
    ``learned/pytest/async-patterns``), the lexicographically-first ref
    wins. Deterministic; never depends on iteration order.

    Generic: this function holds no project-specific knowledge. The
    precedence policy is a parameter; pass any tuple at the call site.

    Parameters
    ----------
    refs : iterable of refs like ``"project/foo"``,
        ``"learned/cat/bar"``, ``"builtin/baz"``. Empty strings, refs
        with fewer than 2 parts, and refs whose scope is not in
        ``scope_precedence`` are silently dropped.
    scope_precedence : tuple of scope strings, earliest = highest
        precedence. Defaults to ``SKILL_SCOPES``.

    Returns
    -------
    FrozenSet[str] of canonical refs (the originally-passed strings,
    preserving any category prefix on the winning ref).
    """
    precedence_index = {scope: i for i, scope in enumerate(scope_precedence)}

    # Map terminal_name → list of (precedence_rank, ref_str)
    candidates: Dict[str, List[Tuple[int, str]]] = {}
    for raw in refs:
        if not raw:
            continue
        ref = str(raw)
        parts = ref.split("/")
        if len(parts) < 2:
            continue
        scope = parts[0]
        if scope not in precedence_index:
            continue
        terminal = parts[-1]
        if not terminal:
            continue
        rank = precedence_index[scope]
        candidates.setdefault(terminal, []).append((rank, ref))

    survivors: List[str] = []
    for _terminal, options in candidates.items():
        # Sort by (rank ascending, ref ascending). First wins.
        options.sort(key=lambda x: (x[0], x[1]))
        survivors.append(options[0][1])

    return frozenset(survivors)

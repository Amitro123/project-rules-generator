"""tag ∩ tech_stack filter for skill selection.

The missing invariant that produced Bug4 / Bug6 / Bugs.md (49 Python skills
leaked into a JS/agent project, jest skills leaked into a pure-Python bot):
learned skills tagged ``[jest, react]`` were getting selected for projects
whose tech_stack contained zero overlap with those tags.

``filter_skills_by_tech_overlap`` is a generic function over a candidate
ref set, a tech_stack, and an injected tag-resolver callable. The caller
provides the resolver — the function itself has zero knowledge of where
``SKILL.md`` frontmatter lives, how tags are parsed, or which scope is
which.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, FrozenSet, List, Set, Tuple, Union


@dataclass(frozen=True)
class FilterTrace:
    """Records one skill that the tag-overlap filter dropped, plus the
    reason. Surfaces in shadow logs so users can see *why* a skill the
    matcher selected didn't end up in the final set."""

    skill_ref: str
    skill_tags: FrozenSet[str]
    project_tech: FrozenSet[str]
    reason: str


# A tag-resolver maps a skill ref to its declared tags. Returning an empty
# set means "this skill has no declared tags". The filter treats no-tag
# skills as conservative-keep (see keep_when_no_tags below) since the
# resolver can't disprove relevance.
TagResolver = Callable[[str], FrozenSet[str]]


def filter_skills_by_tech_overlap(
    selected_refs: Union[Set[str], FrozenSet[str]],
    tech_stack: Union[Set[str], FrozenSet[str]],
    tag_resolver: TagResolver,
    *,
    scopes_to_filter: FrozenSet[str] = frozenset({"learned"}),
    keep_when_no_tags: bool = True,
) -> Tuple[FrozenSet[str], Tuple[FilterTrace, ...]]:
    """Drop skill refs whose declared tags don't overlap the project's tech.

    Pure function. The caller provides the tag_resolver — the filter has
    no knowledge of file paths, frontmatter parsing, or which directory
    a skill lives in. Same generic shape as
    ``apply_tech_cleanup_rules``: data in, data out, traces describe
    what changed.

    Parameters
    ----------
    selected_refs : refs like 'learned/fastapi/async-patterns' or
        'builtin/code-review' or 'project/foo'. May be a set or frozenset.
    tech_stack : the project's tech_stack (lowercase strings).
    tag_resolver : (skill_ref) -> frozenset of tags. Receives the FULL
        ref. May return ``frozenset()`` for unknown skills (resolver
        couldn't find them). Should not raise; if it does, the skill is
        kept (conservative).
    scopes_to_filter : which scopes the filter applies to (default:
        ``{"learned"}``). Builtin skills are universal; project skills
        are project-specific by definition — both bypass the filter.
    keep_when_no_tags : how to handle a skill whose resolver returned
        an empty tag set. True (default) = keep the skill — absence of
        tags isn't proof of irrelevance. False = drop it (strict).

    Returns
    -------
    (filtered_refs, traces) :
        * filtered_refs : the surviving subset of selected_refs as a
          new frozenset.
        * traces : tuple of FilterTrace records, one per dropped skill.
          Empty when nothing was filtered out.
    """
    project_tech_norm = frozenset(t.lower() for t in tech_stack)
    survivors: List[str] = []
    traces: List[FilterTrace] = []

    for ref in selected_refs:
        if not ref:
            continue
        parts = str(ref).split("/")
        scope = parts[0] if parts else ""

        # Scopes outside the filter set bypass it entirely.
        if scope not in scopes_to_filter:
            survivors.append(ref)
            continue

        # Look up the skill's tags via the injected resolver. Any exception
        # in user code is treated as "tags unknown" (conservative keep).
        try:
            tags_raw = tag_resolver(ref)
        except Exception:  # noqa: BLE001 — resolver is user code; never crash the filter
            survivors.append(ref)
            continue

        skill_tags = frozenset(t.lower() for t in (tags_raw or frozenset()))

        if not skill_tags:
            if keep_when_no_tags:
                survivors.append(ref)
            else:
                traces.append(
                    FilterTrace(
                        skill_ref=ref,
                        skill_tags=skill_tags,
                        project_tech=project_tech_norm,
                        reason="strict_mode_no_tags: skill has no declared tags",
                    )
                )
            continue

        overlap = skill_tags & project_tech_norm
        if overlap:
            survivors.append(ref)
        else:
            traces.append(
                FilterTrace(
                    skill_ref=ref,
                    skill_tags=skill_tags,
                    project_tech=project_tech_norm,
                    reason="no_tag_overlap: skill's tags have zero intersection with project tech_stack",
                )
            )

    return frozenset(survivors), tuple(traces)

"""ProjectProfile core dataclasses — the immutable contract.

``TechEntry`` is one tech with its evidence source. ``SkillRef`` is one
selected skill keyed by (scope, terminal name). ``ProjectProfile`` is the
frozen snapshot constructed once per pipeline run; its
``validate_invariants()`` and ``validate_against_disk()`` methods are the
single place where the producer/consumer contract is enforced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

from generator.project_profile.constants import (
    EVIDENCE_SOURCES_ALL,
    EVIDENCE_SOURCES_STRONG,
    GENERIC_PROJECT_NAME_SLUGS,
    KNOWN_PROJECT_TYPES,
    PROJECT_NAME_MAX_LENGTH,
    PROJECT_NAME_MAX_SEGMENTS,
    SKILL_SCOPES,
    looks_like_concatenated_heading_slug,
)
from generator.project_profile.exceptions import InvariantViolation


@dataclass(frozen=True)
class TechEntry:
    """One detected technology with the evidence that supports it.

    ``source`` answers "how do we know this is in the stack?". A tech with
    only README evidence is weaker than one backed by requirements.txt.
    Some project_type rules (see Phase 3) strip README-only tech that
    contradicts the project's primary identity — e.g. a Reflex project's
    "react" mention from README prerequisites is README-only and gets
    stripped, but a real React project's "react" in package.json is a
    manifest source and stays.
    """

    name: str
    source: str  # one of EVIDENCE_SOURCES_ALL

    def is_strong(self) -> bool:
        return self.source in EVIDENCE_SOURCES_STRONG


@dataclass(frozen=True)
class SkillRef:
    """A reference to a single skill. Canonical key for dedup."""

    scope: str  # one of SKILL_SCOPES
    name: str  # terminal name, no path or category prefix

    @property
    def ref(self) -> str:
        """Path-style ref used in clinerules.yaml: 'project/foo', 'learned/bar'."""
        return f"{self.scope}/{self.name}"


@dataclass(frozen=True)
class ProjectProfile:
    """Immutable snapshot of a project's identity after all detectors finish.

    Construct with ``from_enhanced_context()``; never mutate.

    Fields
    ------
    project_name : canonical project name (folder slug, not a README heading)
    project_path : absolute path to the project root
    project_type : one of KNOWN_PROJECT_TYPES
    tech_stack   : tuple of TechEntry (immutable, order-stable for diffing)
    selected_skills : tuple of SkillRef — the canonical selection that drives
        BOTH the on-disk file copy AND the clinerules.yaml skills_count.
        Single source of truth.
    has_tests / has_docker / has_ci : signals
    languages : detected source languages
    confidence : detector confidence in (0.0, 1.0)
    """

    project_name: str
    project_path: Path
    project_type: str
    tech_stack: Tuple[TechEntry, ...]
    selected_skills: Tuple[SkillRef, ...]
    languages: Tuple[str, ...] = field(default_factory=tuple)
    has_tests: bool = False
    has_docker: bool = False
    has_ci: bool = False
    confidence: float = 0.0

    # ---- Derived views --------------------------------------------------

    def tech_names(self) -> FrozenSet[str]:
        """Just the tech names, no source — for fast membership checks."""
        return frozenset(t.name for t in self.tech_stack)

    def skill_names(self, scope: Optional[str] = None) -> FrozenSet[str]:
        """Skill terminal names, optionally filtered by scope."""
        if scope is None:
            return frozenset(s.name for s in self.selected_skills)
        return frozenset(s.name for s in self.selected_skills if s.scope == scope)

    def skill_refs_by_scope(self) -> Dict[str, List[str]]:
        """Selected skills grouped by scope. Useful for writers."""
        result: Dict[str, List[str]] = {s: [] for s in SKILL_SCOPES}
        for sk in self.selected_skills:
            if sk.scope in result:
                result[sk.scope].append(sk.name)
        for scope in result:
            result[scope].sort()
        return result

    # ---- Invariants -----------------------------------------------------

    def validate_invariants(self, strict: bool = False) -> List[str]:
        """Check every invariant. Raise on violation when strict=True,
        otherwise return the list of violation messages for the caller
        to log or surface.

        Invariants enforced
        -------------------
        1. project_type is a known value
        2. project_name is not a generic instruction-heading slug
        3. tech_stack has no duplicate names
        4. no skill name appears in two different scopes
           (this is the Bug nbug.md case: pydantic-validation in both
           project/ and learned/)
        5. no project_type rejects a primary tech of its stack
           (sanity check; full per-type rules come in Phase 3)
        6. confidence is in [0.0, 1.0]
        """
        violations: List[str] = []

        if self.project_type not in KNOWN_PROJECT_TYPES:
            violations.append(f"unknown_project_type: {self.project_type!r} not in KNOWN_PROJECT_TYPES")

        if self.project_name in GENERIC_PROJECT_NAME_SLUGS:
            violations.append(
                f"generic_project_name: {self.project_name!r} looks like a README "
                "instruction heading, not a project name. Falling back to the "
                "project directory name is required."
            )

        if looks_like_concatenated_heading_slug(self.project_name):
            violations.append(
                f"oversized_project_name: {self.project_name!r} has "
                f"{self.project_name.count('-') + 1} segments / "
                f"{len(self.project_name)} chars — exceeds "
                f"{PROJECT_NAME_MAX_SEGMENTS} segments or {PROJECT_NAME_MAX_LENGTH} chars. "
                "Almost certainly a concatenated README H1, not a real project "
                "name. The name extractor should fall back to the project "
                "directory name."
            )

        seen_tech: Dict[str, str] = {}
        for entry in self.tech_stack:
            if entry.name in seen_tech:
                violations.append(
                    f"duplicate_tech: {entry.name!r} appears with sources "
                    f"{seen_tech[entry.name]!r} and {entry.source!r}"
                )
            else:
                seen_tech[entry.name] = entry.source
            if entry.source not in EVIDENCE_SOURCES_ALL:
                violations.append(f"unknown_tech_source: {entry.name!r} has source {entry.source!r}")

        seen_skill: Dict[str, str] = {}
        for sk in self.selected_skills:
            if sk.scope not in SKILL_SCOPES:
                violations.append(f"unknown_skill_scope: {sk.ref!r} has scope {sk.scope!r}")
            if sk.name in seen_skill and seen_skill[sk.name] != sk.scope:
                violations.append(
                    f"skill_name_collision: {sk.name!r} appears in both "
                    f"scope {seen_skill[sk.name]!r} and {sk.scope!r}"
                )
            else:
                seen_skill[sk.name] = sk.scope

        if not (0.0 <= self.confidence <= 1.0):
            violations.append(f"confidence_out_of_range: {self.confidence!r} not in [0.0, 1.0]")

        if strict and violations:
            raise InvariantViolation(
                invariant="multiple",
                message="; ".join(violations),
            )
        return violations

    def validate_against_disk(self, output_dir: Path, strict: bool = False) -> List[str]:
        """Assert that ``selected_skills`` filtered by scope='project' matches
        the set of directories under ``output_dir/skills/project/``.

        This is the invariant that catches newbug.md ("9 dirs on disk, rules
        says project: 0"). Called by writers right before they serialize
        clinerules.yaml so the YAML is guaranteed consistent with the
        filesystem at the moment of writing.
        """
        violations: List[str] = []
        project_skills_dir = output_dir / "skills" / "project"

        on_disk: FrozenSet[str] = frozenset()
        if project_skills_dir.exists():
            on_disk = frozenset(
                p.name for p in project_skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
            )

        in_profile = self.skill_names(scope="project")

        missing_in_profile = on_disk - in_profile
        missing_on_disk = in_profile - on_disk

        if missing_in_profile:
            violations.append(
                f"skill_set_disk_mismatch: {len(missing_in_profile)} skill(s) "
                f"on disk but not in selected_skills: {sorted(missing_in_profile)}"
            )
        if missing_on_disk:
            violations.append(
                f"skill_set_disk_mismatch: {len(missing_on_disk)} skill(s) "
                f"in selected_skills but not on disk: {sorted(missing_on_disk)}"
            )

        if strict and violations:
            raise InvariantViolation(
                invariant="skill_set_disk_mismatch",
                message="; ".join(violations),
            )
        return violations

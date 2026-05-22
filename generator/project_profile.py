"""ProjectProfile — single immutable construction site for a project's identity.

This module owns the contract between PRG's detection layer (tech_detector,
project_type_detector, readme_parser, skill_discovery, enhanced_skill_matcher)
and its output layer (rules.md, clinerules.yaml, skills/index.md).

Why this exists
---------------
Historically PRG produced these fields via several independent subsystems that
each wrote into a shared mutable dict (`project_data`). Every recurring bug
traced to one symptom: producers got out of sync with consumers and nothing
enforced an invariant between them — 9 project skills on disk while
`rules.md` reported `project: 0`, `pydantic-validation` appearing in two
scopes, learned skills tagged `[jest, react]` selected for pure-Python
projects, and so on.

ProjectProfile is constructed once after all detectors have run, then frozen.
``validate_invariants()`` is the single place that enforces the contract;
violations raise ``InvariantViolation`` rather than silently degrading.

Phase 1 scope (this file)
-------------------------
Adapter ``from_enhanced_context()`` builds a ProjectProfile from the existing
pipeline's `enhanced_context` dict WITHOUT modifying any producer. Later
phases (see ``Plans/prg-systemic-bug-refactor.md``) migrate producers to
write directly into ProjectProfile, then move the reconciliation cascade
from ``enhanced_parser._extract_metadata`` into ``ProjectProfile.reconcile``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

# --- Constants ---------------------------------------------------------------

# Evidence sources for a tech entry.
#
# STRONG: code-level evidence — the tech is genuinely used by this project.
#   - "dependency"   : appears in requirements.txt / pyproject.toml / package.json
#   - "manifest"     : appears in another machine-readable manifest (spec.yml, etc.)
#   - "import"       : referenced via an import/require statement
#   - "file_pattern" : presence of a signature file (Dockerfile, rxconfig.py, …)
#   - "spec"         : declared in the project's spec.yml / spec.yaml
#
# WEAK: only README / prose evidence — may be aspirational or noise.
#
# UNKNOWN: the producer didn't record a source. Common during Phase 1, when
# the contract is built from a legacy enhanced_context that doesn't carry
# source attribution. Phase 2 migrates detectors to emit explicit sources.
EVIDENCE_SOURCES_STRONG = frozenset({"dependency", "manifest", "import", "file_pattern", "spec"})
EVIDENCE_SOURCES_WEAK = frozenset({"readme"})
EVIDENCE_SOURCES_UNKNOWN = frozenset({"inferred"})
EVIDENCE_SOURCES_ALL = EVIDENCE_SOURCES_STRONG | EVIDENCE_SOURCES_WEAK | EVIDENCE_SOURCES_UNKNOWN

# Skill scopes. Order matters for precedence (project beats learned beats
# builtin when the same terminal name appears in multiple scopes).
SKILL_SCOPES: Tuple[str, ...] = ("project", "learned", "builtin")

# Project types PRG knows how to reason about. Detection layers may produce
# values outside this set during transition — `validate_invariants` flags
# unknown types as a warning rather than a hard error in Phase 1.
KNOWN_PROJECT_TYPES: FrozenSet[str] = frozenset(
    {
        # From generator/analyzers/structure_analyzer.py:PATTERNS
        "python-cli",
        "fastapi-api",
        "django-app",
        "flask-app",
        "reflex-app",
        "react-app",
        "vue-app",
        "node-api",
        "ml-pipeline",
        "library",
        # From generator/analyzers/project_type_detector.py:TYPE_LABEL_MAP
        "python-api",
        "agent-skills",
        "cli-tool",
        "web-app",
        # From override branches in enhanced_parser.py:_extract_metadata
        "agent",
        "generator",
        # Universal fallback
        "unknown",
    }
)

# Project names that came from generic README instruction headings rather
# than the project itself. Detection layers should reject these and fall
# back to the project directory name.
GENERIC_PROJECT_NAME_SLUGS: FrozenSet[str] = frozenset(
    {
        "clone-repository",
        "getting-started",
        "quick-start",
        "installation",
        "setup",
        "introduction",
        "overview",
        "usage",
        "table-of-contents",
        "contents",
    }
)


# --- Exceptions --------------------------------------------------------------


class InvariantViolation(Exception):
    """Raised when a ProjectProfile's invariants fail validation.

    Each violation message includes the failing invariant name (e.g.
    ``skill_set_disk_mismatch``) so callers can route the error or print
    a remediation hint without parsing the message body.
    """

    def __init__(self, invariant: str, message: str) -> None:
        super().__init__(f"[{invariant}] {message}")
        self.invariant = invariant
        self.message = message


# --- Value objects -----------------------------------------------------------


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


# --- ProjectProfile ----------------------------------------------------------


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


# --- Adapters ---------------------------------------------------------------


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

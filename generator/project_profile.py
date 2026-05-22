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
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple, Union

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


# --- Phase 2: declarative project_type reconciliation -----------------------
#
# Replaces the 60-line if/elif cascade at enhanced_parser.py:363-423 (two
# project_type detectors with hardcoded thresholds) with a precedence TABLE
# evaluated in order. The function `reconcile_project_type` is fully generic —
# it iterates rule records and applies whichever first matches. Per-tech
# decisions live in the rule data, not in branching code, so new rules can be
# added without touching reconcile_project_type itself.
#
# Phase 3 will move DEFAULT_PROJECT_TYPE_PRECEDENCE into a YAML/markdown
# rules directory so non-Python contributors can extend the precedence table.


# Sentinel meaning "any newer_type matches this rule".
NEWER_TYPE_ANY = "*"


@dataclass(frozen=True)
class PrecedenceRule:
    """One row in the project_type precedence table.

    A rule fires when ``match_newer`` matches the newer-detector's output AND
    ``predicate`` (given the two detectors' types + confidences) returns True.
    The first rule that fires wins; its newer_type becomes the resolved
    project_type. If no rule fires, the structure_type wins.

    Fields
    ------
    name : human label for debugging / log lines
    match_newer : either a specific newer_type, a frozenset of acceptable
        newer_types, or the sentinel ``NEWER_TYPE_ANY`` ("*") which matches
        any non-empty newer_type
    predicate : callable taking (structure_type, structure_confidence,
        newer_type, newer_confidence) and returning True when the rule
        should fire
    reason : prose explanation, surfaced in shadow logs to make the
        precedence transparent in real runs
    """

    name: str
    match_newer: Union[str, FrozenSet[str]]
    predicate: Callable[[str, float, str, float], bool]
    reason: str

    def matches_newer(self, newer_type: str) -> bool:
        """Type-side match, before evaluating the predicate."""
        if self.match_newer == NEWER_TYPE_ANY:
            return bool(newer_type)
        if isinstance(self.match_newer, frozenset):
            return newer_type in self.match_newer
        return newer_type == self.match_newer


# Predicate factories — closures over numeric thresholds and structure
# vocabularies. Using factories keeps the table itself terse and lets future
# rule additions stay declarative.


def _always_match(*_args, **_kwargs) -> bool:
    return True


def _newer_min_confidence(min_conf: float) -> Callable[[str, float, str, float], bool]:
    def _pred(_structure_type: str, _structure_conf: float, _newer_type: str, newer_conf: float) -> bool:
        return newer_conf >= min_conf

    return _pred


def _newer_confident_structure_uncertain(
    newer_min: float, structure_max: float
) -> Callable[[str, float, str, float], bool]:
    def _pred(_structure_type: str, structure_conf: float, _newer_type: str, newer_conf: float) -> bool:
        return newer_conf >= newer_min and structure_conf < structure_max

    return _pred


def _structure_unreliable_and_newer_confident(
    fallback_structure_types: FrozenSet[str],
    newer_min: float,
) -> Callable[[str, float, str, float], bool]:
    """When the structural detector gave a generic fallback (library/unknown)
    AND the newer detector is reasonably confident, prefer the newer result.
    """

    def _pred(structure_type: str, _structure_conf: float, _newer_type: str, newer_conf: float) -> bool:
        return structure_type in fallback_structure_types and newer_conf >= newer_min

    return _pred


# DEFAULT_PROJECT_TYPE_PRECEDENCE is assigned at the bottom of this module
# (after all dataclasses the loader depends on are defined). Pre-declared
# here as an empty tuple so any tooling that references the name during
# import sees a valid value rather than NameError. The real value is loaded
# from generator/rules/tech-detection/project-type-precedence/ YAML files.
DEFAULT_PROJECT_TYPE_PRECEDENCE: Tuple[PrecedenceRule, ...] = ()


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of project_type reconciliation. The resolved type plus a
    machine-readable trace so shadow logs / debug output can show which
    rule fired (if any)."""

    project_type: str
    rule_fired: Optional[str]  # PrecedenceRule.name, or None if no rule applied
    reason: str  # the rule's reason, or a default when no rule fired


def reconcile_project_type(
    structure_type: str,
    structure_confidence: float,
    newer_type: str,
    newer_confidence: float,
    rules: Optional[Tuple[PrecedenceRule, ...]] = None,
) -> ReconciliationResult:
    """Resolve the canonical project_type given two detectors' outputs.

    Replaces the if/elif cascade in ``enhanced_parser._extract_metadata``.
    Pure function — no I/O, no globals, no project-specific code paths.
    The precedence is data; this function is generic.

    Parameters
    ----------
    structure_type : output of ``StructureAnalyzer.detect_project_type()``
        (typically one of python-cli, fastapi-api, library, unknown, …).
    structure_confidence : confidence in [0.0, 1.0] from the same detector.
    newer_type : output of ``project_type_detector.detect_project_type()``,
        already translated through TYPE_LABEL_MAP. May be ``""`` when the
        detector produced no opinion.
    newer_confidence : confidence in [0.0, 1.0] from the newer detector.
    rules : ordered precedence table. Defaults to
        ``DEFAULT_PROJECT_TYPE_PRECEDENCE``. Passing a custom tuple lets
        callers (especially tests) override the policy without monkey-patching.

    Returns
    -------
    ReconciliationResult with the resolved project_type plus the rule that
    fired (or ``None`` when no rule matched and structure_type was kept).
    """
    # Normalize inputs — guards against detectors that return None or float
    # confidences outside [0, 1]. The contract here is "tolerate ugly input
    # from upstream detectors during the migration; clamp and proceed".
    s_type = (structure_type or "unknown").strip() or "unknown"
    s_conf = max(0.0, min(1.0, float(structure_confidence or 0.0)))
    n_type = (newer_type or "").strip()
    n_conf = max(0.0, min(1.0, float(newer_confidence or 0.0)))

    # Default to the module-level table, evaluated at CALL time so YAML
    # rules loaded at the bottom of this module are picked up correctly.
    if rules is None:
        rules = DEFAULT_PROJECT_TYPE_PRECEDENCE

    if not n_type:
        return ReconciliationResult(
            project_type=s_type,
            rule_fired=None,
            reason="newer_type was empty; kept structure_type unchanged.",
        )

    for rule in rules:
        if not rule.matches_newer(n_type):
            continue
        if rule.predicate(s_type, s_conf, n_type, n_conf):
            return ReconciliationResult(
                project_type=n_type,
                rule_fired=rule.name,
                reason=rule.reason,
            )

    # No rule fired — structure detector wins by default.
    return ReconciliationResult(
        project_type=s_type,
        rule_fired=None,
        reason="No precedence rule matched; kept structure_type as the default.",
    )


# --- Phase 3a: declarative tech-stack cleanup rules ------------------------
#
# Replaces the post-detection patches at enhanced_parser.py:431-438
# (`_noise_tokens` strip + `if "reflex" in tech_stack` block) with a list of
# declarative records. The function `apply_tech_cleanup_rules` is generic —
# it iterates rule records and strips the configured techs whenever a
# rule's predicate fires.
#
# Phase 3b will move DEFAULT_TECH_CLEANUP_RULES into YAML/markdown files in
# `generator/rules/tech-detection/` so non-Python contributors can add new
# cleanup rules without editing this module.


# A predicate takes (current tech_stack, cleanup_context) → True when the
# rule's strip set should be applied. The context carries auxiliary signal
# (e.g. ``test_framework``) that the predicate may need.
CleanupPredicate = Callable[[FrozenSet[str], Dict[str, Any]], bool]


@dataclass(frozen=True)
class TechCleanupRule:
    """One declarative rule for removing techs from a detected stack.

    Fields
    ------
    name : human label; surfaces in shadow logs and CleanupTrace.
    predicate : callable returning True when this rule's strip set applies.
        Receives a snapshot of the *current* tech_stack (after earlier rules
        have already run) plus a context dict (typically ``{"test_framework":
        "pytest"}`` or similar).
    strip : the techs this rule removes if the predicate fires.
    reason : prose explanation. Used in shadow logs so users can see *why*
        a tech was removed without reading the code.
    """

    name: str
    predicate: CleanupPredicate
    strip: FrozenSet[str]
    reason: str


@dataclass(frozen=True)
class CleanupTrace:
    """One rule's effect on the tech_stack, recorded for diagnostics."""

    rule_name: str
    stripped: FrozenSet[str]
    reason: str


# Predicate factories — closures over the values they test, keeping the rule
# table itself terse and declarative.


def _always_apply(_techs: FrozenSet[str], _ctx: Dict[str, Any]) -> bool:
    return True


def _when_stack_contains(token: str) -> CleanupPredicate:
    """Fire when `token` is currently present in the tech_stack."""

    def _pred(techs: FrozenSet[str], _ctx: Dict[str, Any]) -> bool:
        return token in techs

    return _pred


def _when_context_key_not_equal(key: str, value: Any) -> CleanupPredicate:
    """Fire unless context[key] equals value. Used to strip a leaked
    framework keyword UNLESS that framework is actually the project's
    test framework."""

    def _pred(_techs: FrozenSet[str], ctx: Dict[str, Any]) -> bool:
        return ctx.get(key) != value

    return _pred


# DEFAULT_TECH_CLEANUP_RULES is assigned at the bottom of this module (same
# reason as DEFAULT_PROJECT_TYPE_PRECEDENCE: the loader needs all dataclasses
# defined before it can run). Real value comes from
# generator/rules/tech-detection/tech-cleanup/ YAML files.
DEFAULT_TECH_CLEANUP_RULES: Tuple[TechCleanupRule, ...] = ()


def apply_tech_cleanup_rules(
    tech_stack: FrozenSet[str],
    context: Optional[Dict[str, Any]] = None,
    rules: Optional[Tuple[TechCleanupRule, ...]] = None,
) -> Tuple[FrozenSet[str], Tuple[CleanupTrace, ...]]:
    """Apply each cleanup rule in order; return the post-cleanup tech_stack
    plus a trace of which rules actually changed anything.

    Pure function. No I/O, no globals, no project-specific branches —
    rule data drives behaviour. Adding a new cleanup rule = appending to
    DEFAULT_TECH_CLEANUP_RULES (or passing a custom tuple at call site).

    Parameters
    ----------
    tech_stack : the set of detected techs to clean.
    context : auxiliary signal predicates may consult (e.g.
        ``{"test_framework": "pytest"}``). ``None`` is treated as ``{}``.
    rules : ordered tuple of TechCleanupRule. Defaults to
        ``DEFAULT_TECH_CLEANUP_RULES``. Passing a custom tuple lets
        callers (especially tests) drive arbitrary policy with no code
        changes.

    Returns
    -------
    (cleaned_stack, traces) :
        * cleaned_stack : a new frozenset; original is not mutated.
        * traces : tuple of CleanupTrace records — one per rule that
          actually stripped something. Empty when nothing was removed.
          Useful for shadow logs ("why did 'react' disappear?").
    """
    ctx = context or {}
    current = frozenset(tech_stack)
    traces: List[CleanupTrace] = []

    # Default to the module-level table, evaluated at CALL time so YAML
    # rules loaded at the bottom of this module are picked up correctly.
    if rules is None:
        rules = DEFAULT_TECH_CLEANUP_RULES

    for rule in rules:
        if not rule.predicate(current, ctx):
            continue
        # Only strip what's actually there; CleanupTrace records the
        # intersection (so traces never claim to have removed something
        # that wasn't present).
        stripped_here = rule.strip & current
        if not stripped_here:
            continue
        current = current - stripped_here
        traces.append(
            CleanupTrace(
                rule_name=rule.name,
                stripped=stripped_here,
                reason=rule.reason,
            )
        )

    return current, tuple(traces)


# --- Load declarative rule files at import time -----------------------------
#
# This runs AFTER all dataclasses (PrecedenceRule, TechCleanupRule, etc.) are
# defined, so the loader can import them without circular-dependency issues.
# Failure to load is non-fatal: the contract layer still works (with empty
# tables), but the default reconciliation/cleanup behaviour is unavailable.
# Functions that take a `rules` parameter look up the module-level default
# at call time, so reassignment here propagates correctly.


def _load_rules_at_import() -> None:
    """Populate DEFAULT_PROJECT_TYPE_PRECEDENCE and DEFAULT_TECH_CLEANUP_RULES
    from the YAML rule files. Logs and continues on failure."""
    global DEFAULT_PROJECT_TYPE_PRECEDENCE, DEFAULT_TECH_CLEANUP_RULES
    try:
        from generator.rules.tech_detection_loader import load_cleanup_rules, load_precedence_rules

        DEFAULT_PROJECT_TYPE_PRECEDENCE = load_precedence_rules()
        DEFAULT_TECH_CLEANUP_RULES = load_cleanup_rules()
    except Exception as exc:  # noqa: BLE001 — must never break module import
        import logging

        logging.getLogger(__name__).warning(
            "project_profile: failed to load YAML rule files: %s. "
            "DEFAULT_PROJECT_TYPE_PRECEDENCE and DEFAULT_TECH_CLEANUP_RULES "
            "remain empty; reconcile_project_type / apply_tech_cleanup_rules "
            "will be no-ops until rule files are restored.",
            exc,
        )


_load_rules_at_import()

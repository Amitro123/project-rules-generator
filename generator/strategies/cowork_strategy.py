"""Cowork analysis strategy for skill generation.

This module provides a high-level strategy to generate skills using a Cowork
project analysis flow. It aims to:
- Validate inputs and guard against common error cases
- Supplement insufficient README context with a lightweight project analysis
- Delegate skill creation to a creator component (injected for testability)
- Provide structured logging and consistent return semantics

Security/robustness considerations:
- No external I/O is performed here beyond delegating to collaborators
- All collaborator calls are wrapped with defensive error handling
- Inputs are validated to avoid None/empty values and missing paths

Design:
- The strategy depends on an abstracted "creator" via a protocol to allow
  dependency injection in tests. By default it constructs CoworkSkillCreator
  lazily to avoid import cycles at import time.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Protocol, Tuple

from generator.utils.readme_bridge import bridge_missing_context, is_readme_sufficient

if TYPE_CHECKING:  # import for typing only to avoid circular import costs at runtime
    from generator.skill_creator import CoworkSkillCreator  # pragma: no cover


class _QualityProtocol(Protocol):
    """Minimal protocol for the quality object returned by the creator."""

    score: float


class SkillCreatorProtocol(Protocol):
    """Protocol for a skill creator dependency used by this strategy.

    Implementations must create a skill from a name and README-like context and
    return a tuple of (content, metadata, quality). The quality object is
    expected to have a numeric "score" attribute.
    """

    def create_skill(
        self, skill_name: str, readme_content: str, use_ai: bool, provider: str
    ) -> Tuple[str, Mapping[str, Any], _QualityProtocol]:
        ...  # pragma: no cover


# Log message templates (centralized to avoid magic strings)
_LOG_START = "Using Cowork analysis for '%s'"
_LOG_QUALITY = "Cowork quality score: %s/100"
_LOG_FALLBACK = "Cowork generation failed; returning None"


class CoworkStrategy:
    """Generate skills using Cowork's intelligent project analysis.

    This strategy orchestrates bridging missing README context and delegating
    the final skill creation to a creator component.

    Parameters:
        creator_factory: Optional factory to build a SkillCreatorProtocol from a
            project Path. If not provided, a default factory will import and
            instantiate CoworkSkillCreator on demand.
    """

    def __init__(
        self, creator_factory: Optional[Callable[[Path], SkillCreatorProtocol]] = None
    ) -> None:
        self._creator_factory = creator_factory or self._default_creator_factory

    @staticmethod
    def _default_creator_factory(project_path: Path) -> SkillCreatorProtocol:
        """Default factory loading CoworkSkillCreator lazily.

        This is separated to allow dependency injection in tests and to reduce
        import-time coupling.
        """
        # Lazy import to avoid circular imports at module import time
        from generator.skill_creator import CoworkSkillCreator  # type: ignore

        return CoworkSkillCreator(project_path)

    def generate(
        self,
        skill_name: str,
        project_path: Optional[Path],
        from_readme: Optional[str],
        provider: str,
        **kwargs: object,
    ) -> Optional[str]:
        """Generate a skill using Cowork analysis.

        The flow is:
        1. Validate inputs (skill name, provider, path exists/dir)
        2. Use README content if provided; otherwise start with empty content
        3. If README is insufficient, attempt to bridge missing context
        4. Delegate creation to the injected creator

        Returns:
            The generated skill content on success, or None on failure.

        Notes on error handling:
            All collaborator calls are wrapped with try/except and errors are
            logged with context, returning None to keep a consistent contract
            for callers.
        """
        # Input validation
        if not skill_name or not skill_name.strip():
            logging.error("Invalid skill_name provided: empty or whitespace only")
            return None
        if not provider or not provider.strip():
            logging.error("Invalid provider provided: empty or whitespace only")
            return None
        if project_path is None:
            logging.error("project_path is None; cannot proceed")
            return None
        if not isinstance(project_path, Path):
            try:
                project_path = Path(project_path)  # type: ignore[arg-type]
            except Exception as exc:  # defensive cast
                logging.exception("Failed to coerce project_path to Path: %s", exc)
                return None
        if not project_path.exists():
            logging.error("project_path does not exist: %s", project_path)
            return None
        if not project_path.is_dir():
            logging.error("project_path is not a directory: %s", project_path)
            return None

        # Creator construction
        try:
            creator = self._creator_factory(project_path)
        except Exception as exc:
            logging.exception("Failed to create Cowork skill creator: %s", exc)
            return None

        logging.info(_LOG_START, skill_name)

        # Normalize README content
        readme_content = (from_readme or "").strip()

        # Assess README sufficiency and bridge missing context when needed
        try:
            sufficient = is_readme_sufficient(readme_content)
        except Exception as exc:
            logging.exception(
                "Failed to assess README sufficiency for '%s': %s", skill_name, exc
            )
            sufficient = False  # fall back to bridging if unsure

        if not sufficient:
            try:
                supplement = bridge_missing_context(project_path, skill_name)
                if supplement:
                    readme_content = f"{supplement}\n\n{readme_content}" if readme_content else supplement
            except Exception as exc:
                logging.exception(
                    "Failed to bridge missing context for '%s': %s", skill_name, exc
                )
                # Proceed with whatever README content we have

        # Without AI, CoworkSkillCreator falls back to inline/Jinja2 template
        # generation that parses README content — fine for project-workflow skills
        # but produces garbage for meta-skills (e.g. "readme-improvement").
        # Return None so StubStrategy produces a clean, honest skeleton instead.
        use_ai: bool = bool(kwargs.get("use_ai", False))
        if not use_ai:
            logging.debug("CoworkStrategy: use_ai=False — skipping to StubStrategy")
            return None

        try:
            content, _metadata, quality = creator.create_skill(
                skill_name=skill_name,
                readme_content=readme_content,
                use_ai=use_ai,
                provider=provider,
            )
            try:
                logging.info(_LOG_QUALITY, getattr(quality, "score", "?"))
            except Exception:  # logging should not break flow
                logging.debug("Quality object did not provide a score attribute")
            return content
        except Exception as exc:
            logging.exception("%s: %s", _LOG_FALLBACK, exc)
            return None

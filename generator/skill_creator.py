"""
Cowork-Powered Skill Creator
===========================

This module implements Cowork's intelligent skill creation logic for PRG.
It generates high-quality, project-specific skills with:
- Smart auto-trigger optimization
- Intelligent tool selection
- Quality gates and validation
- Hallucination prevention
- Actionable, specific steps
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from generator.quality_validators import SkillQualityValidator
from generator.skill_content_renderer import SkillContentRenderer
from generator.skill_discovery import SkillDiscovery
from generator.skill_doc_loader import SkillDocLoader
from generator.skill_metadata_builder import SkillMetadataBuilder
from generator.skill_project_scanner import ProjectContextScanner
from generator.tech_registry import TECH_TOOLS as _TECH_TOOLS
from generator.utils.quality_checker import QualityReport

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Structured metadata for skill generation."""

    name: str
    description: str
    auto_triggers: List[str] = field(default_factory=list)
    project_signals: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    category: str = "project"
    priority: int = 50  # 0-100, higher = more priority
    negative_triggers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class CoworkSkillCreator:
    """
    Generates Cowork-quality skills for PRG projects.

    Orchestrates ProjectContextScanner, SkillContentRenderer,
    SkillMetadataBuilder, SkillDocLoader, and SkillQualityValidator.
    """

    # Technology → Required Tools mapping (single source of truth: tech_registry.py)
    TECH_TOOLS = _TECH_TOOLS

    def __init__(self, project_path: Path):
        """Initialize with project path for context awareness."""
        self.project_path = project_path
        self.discovery = SkillDiscovery(project_path)
        self._quality = SkillQualityValidator(project_path)
        self._doc_loader = SkillDocLoader(project_path)
        self._meta_builder = SkillMetadataBuilder(project_path)
        self._scanner = ProjectContextScanner(project_path)
        self._renderer = SkillContentRenderer(project_path, self._scanner, self._meta_builder, self._doc_loader)

    # ------------------------------------------------------------------
    # Skill lifecycle / persistence
    # ------------------------------------------------------------------

    def detect_skill_needs(self, project_path: Path) -> List[str]:
        """Detect needed skills based on tech stack and context.

        Uses SkillGenerator.TECH_SKILL_NAMES as the single source of truth for
        the tech→skill mapping (covers 40+ technologies).
        """
        # Lazy import to avoid circular dependency
        from generator.skill_generator import SkillGenerator

        readme_path = project_path / "README.md"
        readme_content = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path.exists() else ""

        tech_stack = self._detect_tech_stack(readme_content)
        skill_names = []

        if not tech_stack:
            skill_names.append(f"{project_path.name}-workflow")
        else:
            for tech in tech_stack:
                skill_name = SkillGenerator.TECH_SKILL_NAMES.get(tech.lower())
                if skill_name:
                    skill_names.append(skill_name)

            if not skill_names:
                skill_names.append(f"{project_path.name}-workflow")

        return list(set(skill_names))

    def exists_in_learned(self, skill_name: str) -> bool:
        """Check if skill exists in global learned cache.

        Delegates to SkillDiscovery.skill_exists() — single source of truth.
        Checks both flat file (<name>.md) and directory (<name>/SKILL.md) formats.
        """
        return self.discovery.skill_exists(skill_name, scope="learned")

    def save_to_learned(self, skill_name: str, content: str, category: str = "general") -> Path:
        """Save skill to global learned cache using the standard subfolder layout.

        Delegates to SkillPathManager.save_learned_skill() so all callers write
        to the same layout: global_learned/{category}/{name}/SKILL.md.
        """
        from generator.storage.skill_paths import SkillPathManager

        return SkillPathManager.save_learned_skill({"name": skill_name, "content": content}, category)

    def link_from_learned(self, skill_name: str):
        """Link a learned skill from Global Cache to Project Local Skills.

        Supports both storage formats:
        - Flat file: global_learned/<name>.md  → project_local_dir/<name>.md
        - Directory: global_learned/<name>/     → project_local_dir/<name>/
          (DESIGN-2 fix: link the *whole* directory so Level-3 subdirs are included)
        """
        source_flat = self.discovery.global_learned / f"{skill_name}.md"
        source_dir = self.discovery.global_learned / skill_name

        if not self.discovery.project_local_dir:
            logger.warning("Could not link %s: No project path configured.", skill_name)
            return

        if source_flat.exists():
            target = self.discovery.project_local_dir / f"{skill_name}.md"
            self.discovery._link_or_copy(source_flat, target)
        elif source_dir.exists() and source_dir.is_dir():
            target_dir = self.discovery.project_local_dir / skill_name
            target_dir.mkdir(parents=True, exist_ok=True)

            # Always make SKILL.md available at top-level <name>.md for convenience
            src_md = source_dir / "SKILL.md"
            if src_md.exists():
                self.discovery._link_or_copy(src_md, self.discovery.project_local_dir / f"{skill_name}.md")

            for item in source_dir.rglob("*"):
                rel = item.relative_to(source_dir)
                dest = target_dir / rel
                if item.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    self.discovery._link_or_copy(item, dest)
        else:
            logger.warning("Could not link %s: Source not found in global learned.", skill_name)

    def create_skill(
        self,
        skill_name: str,
        readme_content: str,
        tech_stack: Optional[List[str]] = None,
        custom_context: Optional[Dict] = None,
        use_ai: bool = False,
        provider: str = "gemini",
    ) -> Tuple[str, SkillMetadata, QualityReport]:
        """
        Create a Cowork-quality skill with full intelligence.

        Args:
            skill_name: Name of skill (e.g., "fastapi-security-auditor")
            readme_content: Project README content for context
            tech_stack: Technologies used (auto-detected if None)
            custom_context: Additional context (file samples, etc.)

        Returns:
            Tuple of (skill_content, metadata, quality_report)
        """
        # 0. CRITICAL: Analyze ACTUAL project files first — prevents hallucinations
        project_analysis = self._scanner.analyze_project_structure(skill_name, tech_stack)

        if custom_context is None:
            custom_context = {}
        custom_context["project_analysis"] = project_analysis

        # 1. Build metadata with smart triggers
        metadata = self._build_metadata(skill_name, readme_content, tech_stack)

        # 2. Generate skill content (WITH actual project context)
        content = self._renderer.generate_content(skill_name, readme_content, metadata, custom_context, use_ai, provider)

        # 3. Quality validation (will catch hallucinated paths)
        quality = self._quality.validate(content, metadata)

        # 4. If quality is low, attempt auto-fix
        if not quality.passed:
            content = self._quality.auto_fix(content, quality)
            quality = self._quality.validate(content, metadata)

        return content, metadata, quality

    def export_to_file(
        self,
        content: str,
        metadata: SkillMetadata,
        output_dir: Path,
    ) -> Path:
        """Export skill to file in project .clinerules structure."""
        output_dir.mkdir(parents=True, exist_ok=True)
        skill_file = output_dir / f"{metadata.name}.md"
        skill_file.write_text(content, encoding="utf-8")
        return skill_file

    def auto_generate_skills(
        self,
        readme_content: str,
        output_dir: Path,
        quality_threshold: int = 70,
        auto_fix: bool = True,
    ) -> List[Path]:
        """Auto-generate skills based on detected tech stack.

        Returns list of generated file paths.
        """
        tech_stack = self._detect_tech_stack(readme_content)
        skill_names = []

        if not tech_stack:
            skill_names.append(f"{self.project_path.name}-workflow")
        else:
            # Use SkillGenerator.TECH_SKILL_NAMES as the single source of truth (BUG-1 fix)
            from generator.skill_generator import SkillGenerator

            for tech in tech_stack:
                name = SkillGenerator.TECH_SKILL_NAMES.get(tech.lower())
                if name:
                    skill_names.append(name)

            if not skill_names:
                skill_names.append(f"{self.project_path.name}-workflow")

        generated_files = []
        for skill_name in set(skill_names):
            try:
                content, metadata, quality = self.create_skill(skill_name, readme_content)

                if quality.score >= quality_threshold or auto_fix:
                    path = self.export_to_file(content, metadata, output_dir)
                    generated_files.append(path)
            except Exception as e:
                logger.warning("Failed to generate %s: %s", skill_name, e)

        return generated_files

    # ------------------------------------------------------------------
    # Internal helpers (thin delegates kept for backward compatibility)
    # ------------------------------------------------------------------

    def _build_metadata(
        self,
        skill_name: str,
        readme_content: str,
        tech_stack: Optional[List[str]] = None,
    ) -> SkillMetadata:
        """Build smart metadata — delegates to SkillMetadataBuilder."""
        if tech_stack is None:
            tech_stack = self._scanner._detect_tech_stack(readme_content)
        signals = list(self._scanner._detect_project_signals())
        return self._meta_builder.build(skill_name, readme_content, tech_stack, signals)

    def _detect_tech_stack(self, readme_content: str) -> List[str]:
        """Delegate to ProjectContextScanner (cached)."""
        return self._scanner._detect_tech_stack(readme_content)

    def _detect_project_signals(self) -> Set[str]:
        """Delegate to ProjectContextScanner (cached)."""
        return self._scanner._detect_project_signals()

    # -- Test-facing delegates (keep to avoid changing test files) ------

    def _validate_quality(self, content: str, metadata: SkillMetadata) -> QualityReport:
        """Delegate to SkillQualityValidator."""
        return self._quality.validate(content, metadata)

    def _generate_content(
        self,
        skill_name: str,
        readme_content: str,
        metadata: SkillMetadata,
        custom_context: Optional[Dict] = None,
        use_ai: bool = False,
        provider: str = "gemini",
    ) -> str:
        """Delegate to SkillContentRenderer."""
        return self._renderer.generate_content(skill_name, readme_content, metadata, custom_context, use_ai, provider)

    def _generate_with_jinja2(
        self,
        skill_name: str,
        readme_content: str,
        metadata: SkillMetadata,
        custom_context: Optional[Dict] = None,
    ) -> str:
        """Delegate to SkillContentRenderer."""
        return self._renderer._generate_with_jinja2(skill_name, readme_content, metadata, custom_context)

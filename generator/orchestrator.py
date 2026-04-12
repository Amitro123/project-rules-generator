import logging
from typing import Any, Dict, List

from generator.analyzers.needs import ProjectNeedsAnalyzer

from .sources.base import SkillSource
from .types import Skill, SkillNeed

logger = logging.getLogger("project_rules_generator")


class SkillOrchestrator:
    """
    Coordinates the skill generation process:
    Analysis -> Discovery -> Matching -> Adaptation -> Generation -> Learning
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sources: List[SkillSource] = []
        self.analyzer = ProjectNeedsAnalyzer()

    def register_source(self, source: SkillSource):
        """Register a skill source."""
        self.sources.append(source)
        # Sources are sorted by priority (higher index = higher priority).
        # preference_order: [builtin, awesome, learned] → learned (index 2) wins over builtin (index 0).
        self.sources.sort(key=lambda s: s.priority, reverse=True)

    def orchestrate(self, project_data: Dict[str, Any], project_path: str) -> List[Skill]:
        """
        Main orchestration flow.

        Args:
            project_data: Analyzed project data (from README/files)
            project_path: Path to project

        Returns:
            Final list of skills
        """
        # 1. Analysis -> Needs
        needs = self.analyzer.analyze(project_data, project_path)

        # 2. Discovery (Needs-based)
        candidates = self._discover_skills(needs)

        # 2a. Discovery (Auto-Triggers)
        triggered = self._detect_triggered_skills(project_path, project_data)
        candidates.extend(triggered)

        # 3. Matching & Conflict Resolution
        matched_skills = self._match_skills(candidates)

        # 4. Adaptation
        adapted_skills = self._adapt_skills(matched_skills, project_data)

        return adapted_skills

    def _detect_triggered_skills(self, project_path: str, project_data: Dict[str, Any]) -> List[Skill]:
        """Detect skills that should be active based on triggers."""
        from pathlib import Path

        from generator.analyzers.triggers import SkillTriggerDetector

        detector = SkillTriggerDetector(Path(project_path), project_data)
        all_skills = self.list_all_skills()
        triggered = []

        for skill in all_skills:
            # Check match
            matches = detector.match_skill(skill)
            if matches:
                logger.info(f"Auto-triggering skill '{skill.name}': {matches}")
                # Optional: Append validation info
                skill.confidence = 1.0  # Boost confidence
                triggered.append(skill)

        return triggered

    def list_all_skills(self) -> List[Skill]:
        """List all available skills from all sources."""
        all_skills = []
        for source in self.sources:
            try:
                all_skills.extend(source.list_skills())
            except Exception as e:
                logger.error(f"Error listing skills from {source.name}: {e}")
        return all_skills

    def _discover_skills(self, needs: List[SkillNeed]) -> List[Skill]:
        """Query all sources for skills."""
        all_skills = []
        for source in self.sources:
            try:
                found = source.discover(needs)
                all_skills.extend(found)
            except Exception as e:
                # Log error but continue
                logger.error(f"Error discovering from {source.name}: {e}")
        return all_skills

    def _match_skills(self, candidates: List[Skill]) -> List[Skill]:
        """
        Deduplicate and select best skills.
        Relies on source priority (handled by registration order/discover order).
        Since sources are sorted high-priority first, and we iterate them in order in _discover_skills?
        Wait, _discover_skills iterates sources. If `register_source` sorts high->low, then `_discover`
        will find high priority skills first.
        """
        unique_skills: Dict[str, Skill] = {}

        for skill in candidates:
            # If skill name already exists, skip it (because we saw high priority first)
            if skill.name not in unique_skills:
                unique_skills[skill.name] = skill
            else:
                pass  # Expected: higher-priority source already provided this skill

        return list(unique_skills.values())

    def _adapt_skills(self, skills: List[Skill], project_data: Dict[str, Any]) -> List[Skill]:
        """Adapt generic skills to project context."""
        project_name = project_data.get("name", "project")

        for skill in skills:
            # Simple placeholder replacement for project name.
            if skill.description:
                skill.description = skill.description.replace("{project_name}", project_name)

            # Update metadata
            skill.adapted_for = project_name

        return skills

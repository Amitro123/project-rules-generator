import logging
from typing import List, Dict, Any
from .types import Skill, SkillNeed
from .sources.base import SkillSource
from analyzer.needs import ProjectNeedsAnalyzer

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
        # Sort by priority descending (higher number = higher priority? 
        # Wait, usually priority 0 is highest or lowest?
        # Let's enforce: Priority val logic in config is "index in preference_order"
        # Since preference_order is [learned, awesome, builtin] (user said higher index = higher priority?)
        # Actually user said: "preference_order: [builtin, awesome, learned] # learned has highest priority"
        # So index 2 > index 0. 
        # So REVERSE=True is correct sort order for index.
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
        
        # 2. Discovery
        candidates = self._discover_skills(needs)
        
        # 3. Matching & Conflict Resolution
        matched_skills = self._match_skills(candidates)
        
        # 4. Adaptation
        adapted_skills = self._adapt_skills(matched_skills, project_data)
        
        # 5. Generation (TODO: Future phase)
        
        return adapted_skills

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
                # Debug logging
                logger.debug(f"Skipping duplicate skill {skill.name} from lower priority source")
                pass
                
        return list(unique_skills.values())

    def _adapt_skills(self, skills: List[Skill], project_data: Dict[str, Any]) -> List[Skill]:
        """Adapt generic skills to project context."""
        project_name = project_data.get('name', 'project')
        
        for skill in skills:
            # Simple placeholder replacement
            # TODO: More robust Jinja2 templating later
            if skill.description:
                skill.description = skill.description.replace('{project_name}', project_name)
            
            # Update metadata
            skill.adapted_for = project_name
            
        return skills

from pathlib import Path
from typing import List, Dict, Any
import os
import yaml
from ..types import Skill, SkillNeed
from .base import SkillSource

class AwesomeSkillsSource(SkillSource):
    """
    Source that loads skills from an external 'awesome-agent-skills' repository.
    Supports recursive discovery and smart matching based on 'matches' criteria.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        cfg = config.get('skill_sources', {}).get('awesome', {})
        path_str = cfg.get('path', '')
        
        self.enabled = False
        self.skills: Dict[str, Skill] = {}
        
        if not path_str:
            return

        self.path = Path(os.path.expanduser(path_str)).resolve()
        
        if not self.path.exists():
            # In a real app we might log warning, here we just disable
            print(f"Awesome skills path not found: {self.path}")
            return
            
        self.enabled = cfg.get('enabled', False)
        if self.enabled:
            self._load_all_skills()

    @property
    def name(self) -> str:
        return "awesome"

    @property
    def priority(self) -> int:
        order = self.config.get('skill_sources', {}).get('preference_order', [])
        if 'awesome' in order:
            # Return inverted index (0 = highest priority)
            return len(order) - order.index('awesome')
        return 50 # Default medium priority

    def _load_all_skills(self):
        """Recursively load all *.yaml files."""
        for yaml_file in self.path.rglob("*.yaml"):
            try:
                content = yaml.safe_load(yaml_file.read_text(encoding='utf-8'))
                if not content: continue
                
                # Check format: needs 'skill' section or be our standard format
                # The request specifies a specific format: 
                # name, matches, skill: {...}
                if 'skill' in content and 'matches' in content:
                    skill = self._parse_awesome_skill(content)
                    self.skills[skill.name] = skill
                
                # Also support standard format (list of skills) for backward compat/mixing
                elif isinstance(content, list):
                    for s_data in content:
                        s = Skill(**s_data)
                        s.source = "awesome-skills"
                        self.skills[s.name] = s
            except Exception as e:
                print(f"Failed to load {yaml_file}: {e}")

    def _parse_awesome_skill(self, data: Dict[str, Any]) -> Skill:
        """Parse the specific awesome-skills format into a Skill object."""
        skill_content = data.get('skill', {})
        
        # Base fields from top level
        name = data.get('name')
        category = data.get('category', 'general')
        description = data.get('description', '')
        
        # Merge skill content into Skill object fields
        # Skill dataclass has specific fields. We map 'triggers', 'tools' directly.
        # 'when_to_use' likely maps to logic or description? 
        # For now, let's keep extra fields in params or special attributes if Skill supports them.
        # Our types.py Skill has: name, description, category, triggers, tools...
        
        skill = Skill(
            name=name,
            description=description,
            category=category,
            triggers=skill_content.get('triggers', []),
            tools=skill_content.get('tools', []),
            # Map other fields to adaptibility or params
            adaptability={
                'matches': data.get('matches', {}),
                'when_to_use': skill_content.get('when_to_use', []),
                'checks': skill_content.get('checks', [])
            }
        )
        skill.source = "awesome-skills"
        return skill

    def discover(self, needs: List[SkillNeed]) -> List[Skill]:
        if not self.enabled:
            return []

        matched = []
        for need in needs:
            for skill in self.skills.values():
                score = self._calculate_match_score(skill, need)
                if score >= 0.5:  # threshold
                    # Clone skill to avoid mutating the cached one with specific confidence
                    # (dataclass replace or copy)
                    from dataclasses import replace
                    skill_copy = replace(skill)
                    skill_copy.confidence = score
                    matched.append(skill_copy)
        
        return matched

    def _calculate_match_score(self, skill: Skill, need: SkillNeed) -> float:
        score = 0.0
        matches = skill.adaptability.get('matches', {})
        
        # Direct name match (always strong)
        if skill.name == need.name:
            return 1.0
        
        # Check tech_stack match
        if 'tech_stack' in matches:
            tech_stack = matches['tech_stack']
            if need.name in tech_stack:
                score = matches.get('confidence', 0.8)
            # Use 'context' from need if it has tech_stack?
            # Or if need is project_type, maybe matches has project_type?
        
        # Check file match
        # context in need might have 'files' (if we added file detection to needs)
        if 'files' in matches and 'files' in need.context:
            need_files = need.context.get('files', [])
            match_files = matches['files']
            # strict overlap
            file_overlap = set(match_files) & set(need_files)
            if file_overlap:
                score = max(score, 0.7)
        
        return score

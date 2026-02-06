from pathlib import Path
from typing import List, Dict, Any
from ..types import Skill, SkillNeed
from .base import SkillSource
from ..skill_templates import load_skill_from_yaml
import os

class BuiltinSkillsSource(SkillSource):
    """Source that loads skills from the project's templates directory."""
    
    def __init__(self, config: Dict[str, Any], templates_dir: Path = None):
        super().__init__(config)
        
        # Determine path from config or default or injected
        if templates_dir:
             self.templates_path = templates_dir
        else:
             cfg_path = config.get('skill_sources', {}).get('builtin', {}).get('path', 'templates/skills')
             # Resolve relative to project root (assuming we are running from project root or package)
             # Better approach: If relative, assume relative to this file's package parent
             if not os.path.isabs(cfg_path):
                 # generator/sources/builtin.py -> generator/sources -> generator -> project_root -> (cfg_path)
                 # This logic depends on where the code is installed. 
                 # For dev mode (current structure), templates is at project root.
                 # Let's try to find it relative to current file's grandparent
                 current_file = Path(__file__).resolve()
                 project_root = current_file.parent.parent.parent
                 self.templates_path = project_root / cfg_path
             else:
                 self.templates_path = Path(cfg_path)

    @property
    def name(self) -> str:
        return "builtin"

    @property
    def priority(self) -> int:
        order = self.config.get('skill_sources', {}).get('preference_order', [])
        if 'builtin' in order:
            # Return inverted index (0 = highest priority)
            return len(order) - order.index('builtin')
        return 0 # Default low priority

    def discover(self, needs: List[SkillNeed]) -> List[Skill]:
        """
        Scan templates for skills that match the needs.
        Strategy:
        1. List all YAML files in templates directory.
        2. Load them all (caching opportunity here).
        3. Simple name matching: if need.name in skill.name or keyword match.
        """
        if not self.templates_path.exists():
            return []

        found_skills = []
        
        # Load all available builtin skills
        all_builtins = []
        for yaml_file in self.templates_path.glob('*.yaml'):
            try:
                skills = load_skill_from_yaml(yaml_file)
                for s in skills:
                    s.source = "builtin" # tag source
                    all_builtins.append(s)
            except Exception as e:
                # Log error
                pass

        # Match needs
        for need in needs:
            for skill in all_builtins:
                # Exact match on name
                if skill.name == need.name:
                    found_skills.append(skill)
                    continue
                
                # Loose match: need name in skill name (e.g. 'fastapi' in 'fastapi-expert')
                if need.name.lower() in skill.name.lower():
                    found_skills.append(skill)
                    continue
                
                # Category match
                # If the need name matches the skill category (e.g. need.name='core' matches skill.category='core')
                if skill.category == need.name:
                     found_skills.append(skill)
                     continue

        return found_skills

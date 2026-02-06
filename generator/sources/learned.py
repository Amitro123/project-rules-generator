from pathlib import Path
from typing import List, Dict, Any
import os
from ..types import Skill, SkillNeed
from .base import SkillSource
from ..skill_templates import load_skill_from_yaml

class LearnedSkillsSource(SkillSource):
    """Source that loads skills from the user's learned skills directory."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        cfg = config.get('skill_sources', {}).get('learned', {})
        self.enabled = cfg.get('enabled', False)
        self.path_str = cfg.get('path', '~/.project-rules-generator/learned_skills')
        self.auto_save = cfg.get('auto_save', True)
        
        # Expand user path
        self.learned_path = Path(os.path.expanduser(self.path_str)).resolve()
        
        # Create directory if enabled
        if self.enabled and not self.learned_path.exists():
            try:
                self.learned_path.mkdir(parents=True, exist_ok=True)
                # We can't print easily here without verbose flag, but orchestrator might handle logging
            except Exception as e:
                pass # logging.warning(f"Could not create learned skills dir: {e}")

    @property
    def name(self) -> str:
        return "learned"

    @property
    def priority(self) -> int:
        order = self.config.get('skill_sources', {}).get('preference_order', [])
        if 'learned' in order:
             # Return inverted index (0 = highest priority)
            return len(order) - order.index('learned')
        return 100 # Default high priority

    def discover(self, needs: List[SkillNeed]) -> List[Skill]:
        if not self.enabled or not self.learned_path.exists():
            return []

        found_skills = []
        
        # Load all learned skills
        # Assuming learned skills are stored as individual YAMLs or grouped
        all_learned = []
        for yaml_file in self.learned_path.glob('*.yaml'):
            try:
                skills = load_skill_from_yaml(yaml_file)
                for s in skills:
                    s.source = "learned"
                    all_learned.append(s)
            except Exception:
                pass

        # Match needs
        for need in needs:
            for skill in all_learned:
                if skill.name == need.name:
                    found_skills.append(skill)
                    continue
                
                if need.name.lower() in skill.name.lower():
                    found_skills.append(skill)
                    continue
                    
                # Broaden category patching to match Builtin behavior
                # If need name matches skill category (e.g. need.name='core' and skill.category='core')
                if skill.category == need.name:
                     found_skills.append(skill)

        return found_skills
        
    def save_skill(self, skill: Skill):
        """Save a new skill to the learned library."""
        if not self.auto_save:
            return
            
        if not self.learned_path.exists():
            self.learned_path.mkdir(parents=True, exist_ok=True)
            
        # Save as individual file for now
        # We need to serialize the Skill object. 
        # Skill is a dataclass, so we can use asdict but need to handle non-serializable fields if any.
        # But our Skill types are simple.
        try:
            import yaml
            from dataclasses import asdict
            
            file_path = self.learned_path / f"{skill.name}.yaml"
            data = asdict(skill)
            # Remove empty fields to keep it clean? Or keep all?
            # Let's remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            # Write as list of skills (standard format)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump([data], f, sort_keys=False)
                
        except Exception as e:
            print(f"Failed to save skill {skill.name}: {e}")

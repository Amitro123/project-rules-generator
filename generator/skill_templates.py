"""Template management with structured data"""
from pathlib import Path
from typing import Dict, List, Any
import yaml
from functools import lru_cache
from .types import Skill

# Base location for external templates
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates' / 'skills'

@lru_cache(maxsize=10)
def load_skill_template(project_type: str) -> List[Skill]:
    """
    Load skill template from YAML file (cached).
    
    Args:
        project_type: Template name (e.g., agent, ml_pipeline, react)
        
    Returns:
        List of Skill objects
    """
    if not TEMPLATE_DIR.exists():
        # Fallback if directory structure differs
        local_template_dir = Path(__file__).parent.parent / 'templates' / 'skills'
        if local_template_dir.exists():
            template_path = local_template_dir / f"{project_type}.yaml"
        else:
             # Try legacy markdown location just in case, or fail gracefully
             return []
    else:
        template_path = TEMPLATE_DIR / f"{project_type}.yaml"
    
    if not template_path.exists():
        return []
    
    try:
        content = yaml.safe_load(template_path.read_text(encoding='utf-8'))
        skills = []
        if content and 'skills' in content:
            for s_data in content['skills']:
                skills.append(Skill(**s_data))
        return skills
    except Exception as e:
        print(f"Error loading template {project_type}: {e}")
        return []

def get_tech_skills(tech_stack: List[str]) -> List[Skill]:
    """Get skills for specific technologies."""
    skills = []
    # Tech skills are now also stored in YAML templates in the same dir
    for tech in tech_stack:
        tech_skills = load_skill_template(tech)
        if tech_skills:
            for s in tech_skills:
                s.category = 'tech' # Ensure category is set
                skills.append(s)
    return skills

def get_core_skills() -> List[Skill]:
    """Get core generic skills."""
    return load_skill_template('core')

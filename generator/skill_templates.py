"""Template management with structured data"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import List

import yaml

logger = logging.getLogger(__name__)

from .types import Skill

# Base location for external templates
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "skills"


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
        local_template_dir = Path(__file__).parent.parent / "templates" / "skills"
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
        content = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        skills = []
        if content and "skills" in content:
            for s_data in content["skills"]:
                skills.append(Skill(**s_data))
        return skills
    except Exception as e:
        logger.error("Error loading template %s: %s", project_type, e)
        return []


def load_skill_from_yaml(file_path: Path) -> List[Skill]:
    """Load skills from a specific YAML file."""
    if not file_path.exists():
        return []

    try:
        content = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        skills = []
        # Support both list of skills and dict with 'skills' key
        if isinstance(content, list):
            for s_data in content:
                skills.append(Skill(**s_data))
        elif isinstance(content, dict) and "skills" in content:
            for s_data in content["skills"]:
                skills.append(Skill(**s_data))
        return skills
    except Exception as e:
        logger.error("Error loading skills from %s: %s", file_path, e)
        return []

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..skill_templates import load_skill_from_yaml
from ..types import Skill, SkillNeed
from .base import SkillSource

logger = logging.getLogger("project_rules_generator")


class BuiltinSkillsSource(SkillSource):
    """Source that loads skills from the project's templates directory."""

    def __init__(self, config: Dict[str, Any], templates_dir: Optional[Path] = None):
        super().__init__(config)

        # Determine path from config or default or injected
        if templates_dir:
            self.templates_path = templates_dir
        else:
            cfg_path = config.get("skill_sources", {}).get("builtin", {}).get("path", "templates/skills")
            if not os.path.isabs(cfg_path):
                # Templates ship inside the generator package (generator/templates/skills).
                # generator/sources/builtin.py -> generator/sources -> generator (package root).
                # Strip a leading "templates/" in user-provided relative paths so legacy
                # config values keep working after the templates/ -> generator/templates/ move.
                current_file = Path(__file__).resolve()
                package_root = current_file.parent.parent
                normalised = cfg_path.replace("\\", "/").lstrip("./")
                if normalised.startswith("templates/"):
                    normalised = normalised[len("templates/"):]
                self.templates_path = package_root / "templates" / normalised
            else:
                self.templates_path = Path(cfg_path)

    @property
    def name(self) -> str:
        return "builtin"

    @property
    def priority(self) -> int:
        order = self.config.get("skill_sources", {}).get("preference_order", [])
        if "builtin" in order:
            # Return inverted index (0 = highest priority)
            return len(order) - order.index("builtin")
        return 0  # Default low priority

    def _scan_skills(self) -> List[Skill]:
        if not self.templates_path.exists():
            return []

        all_skills = []
        for yaml_file in self.templates_path.glob("*.yaml"):
            try:
                skills = load_skill_from_yaml(yaml_file)
                for s in skills:
                    s.source = "builtin"  # tag source
                    all_skills.append(s)
            except (OSError, ValueError, TypeError) as e:
                logger.warning(f"Failed to load builtin skill {yaml_file}: {e}")
        return all_skills

    def discover(self, needs: List[SkillNeed]) -> List[Skill]:
        """
        Scan templates for skills that match the needs.
        Strategy:
        1. List all YAML files in templates directory.
        2. Load them all (caching opportunity here).
        3. Simple name matching: if need.name in skill.name or keyword match.
        """
        found_skills = []
        all_builtins = self._scan_skills()

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

    def list_skills(self) -> List[Skill]:
        return self._scan_skills()

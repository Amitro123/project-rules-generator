from pathlib import Path
from typing import List, Dict, Optional
from generator.skill_discovery import SkillDiscovery
from generator.skill_parser import SkillParser
from generator.skill_generator import SkillGenerator

class SkillsManager:
    """
    Facade for skill management.
    Delegates to SkillDiscovery, SkillParser, and SkillGenerator.
    """

    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize SkillsManager with Global and Project layers.
        
        Layers:
        1. Project (.clinerules/skills/project) - Metric overrides
        2. Global Learned (~/.project-rules-generator/learned) - User's shared skills
        3. Global Builtin (~/.project-rules-generator/builtin) - Core PRG skills
        """
        self.discovery = SkillDiscovery(project_path)
        self.generator = SkillGenerator(self.discovery)
        
        # Expose paths for backward compatibility if accessed directly
        self.project_path = self.discovery.project_path
        self.global_root = self.discovery.global_root
        self.global_builtin = self.discovery.global_builtin
        self.global_learned = self.discovery.global_learned
        self.project_skills_root = self.discovery.project_skills_root
        self.project_local_dir = self.discovery.project_local_dir

    def ensure_global_structure(self):
        """Ensure global cache directories exist and are synced."""
        self.discovery.ensure_global_structure()

    def setup_project_structure(self):
        """Create project .clinerules/skills structure."""
        self.discovery.setup_project_structure()

    def list_skills(self) -> Dict[str, Dict[str, str]]:
        """List all available skills with their source resolution."""
        return self.discovery.list_skills()

    def resolve_skill(self, skill_name: str) -> Optional[Path]:
        """Find the active skill file based on priority."""
        return self.discovery.resolve_skill(skill_name)

    def create_skill(self, name: str, from_readme: Optional[str] = None, project_path: Optional[str] = None, use_ai: bool = False) -> Path:
        """Create a new learned skill in the GLOBAL cache."""
        return self.generator.create_skill(name, from_readme, project_path, use_ai)

    def generate_from_readme(
        self,
        readme_content: str,
        tech_stack: List[str],
        output_dir: Path,
        project_name: str = "",
        project_path: Optional[Path] = None,
    ) -> List[str]:
        """Generate project-specific learned skills from README and tech stack."""
        return self.generator.generate_from_readme(readme_content, tech_stack, output_dir, project_name, project_path)

    def get_all_skills_content(self) -> Dict[str, Dict]:
        """Get full content of all skills for export (Project > Learned > Builtin)."""
        return self.discovery.get_all_skills_content()

    def extract_all_triggers(self) -> Dict[str, List[str]]:
        """Extract auto-trigger phrases from all skills."""
        all_skills = self.discovery.get_all_skills_content()
        return SkillParser.extract_all_triggers(all_skills)

    def save_triggers_json(self, output_dir: Path):
        """Save extracted triggers to .clinerules/auto-triggers.json"""
        triggers = self.extract_all_triggers()
        SkillParser.save_triggers_json(triggers, output_dir)

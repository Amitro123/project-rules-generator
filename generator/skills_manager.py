from pathlib import Path
from typing import Dict, List, Optional

from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator
from generator.skill_parser import SkillParser


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
        self.project_builtin_link = self.discovery.project_builtin_link
        self.project_learned_link = self.discovery.project_learned_link

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

    def create_skill(
        self,
        name: str,
        from_readme: Optional[str] = None,
        project_path: Optional[str] = None,
        use_ai: bool = False,
        provider: str = "groq",
        force: bool = False,
    ) -> Path:
        """Create a new learned skill in the GLOBAL cache.

        Args:
            force: If True, overwrite an existing skill. Default False (skip).
        """
        return self.generator.create_skill(
            name, from_readme, project_path, use_ai, provider, force=force
        )

    def check_global_skill_reuse(self, tech_stack: List[str]) -> dict:
        """Check which skills already exist globally: 'reuse' | 'adapt' | 'create'.

        Call this before generating skills to surface cross-project reuse decisions.
        Example output::

            {
                'fastapi-endpoints':    'reuse',   # rich skill exists globally
                'dxf-processing':       'adapt',   # stub exists, needs project context
                'konva-nesting-canvas': 'create'   # no skill exists yet
            }
        """
        return self.generator.check_global_skill_reuse(tech_stack)

    def generate_from_readme(
        self,
        readme_content: str,
        tech_stack: List[str],
        output_dir: Path,
        project_name: str = "",
        project_path: Optional[Path] = None,
    ) -> List[str]:
        """Generate project-specific learned skills from README and tech stack."""
        return self.generator.generate_from_readme(
            readme_content, tech_stack, output_dir, project_name, project_path
        )

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

    def _extract_tech_context(self, tech: str, readme_content: str) -> List[str]:
        """Delegate to SkillParser."""
        return SkillParser.extract_tech_context(tech, readme_content)

    def _summarize_purpose(
        self, tech: str, context_lines: List[str], project_name: str
    ) -> str:
        """Delegate to SkillParser."""
        return SkillParser.summarize_purpose(tech, context_lines, project_name)

    def generate_perfect_index(self):
        """
        Auto-generate .clinerules/skills/index.md from all available skills.
        Follows the Perfect Format: Name, Description, Triggers, When to use, Tools, Command, I/O.
        """
        # 1. Get all skills
        all_skills = self.discovery.list_skills()
        
        # 2. Sort skills by type and then name for consistent output
        sorted_skills = []
        for name, data in all_skills.items():
            sorted_skills.append((name, data))
        sorted_skills.sort(key=lambda x: (x[1]['type'], x[0]))

        # 3. Build Index Content
        index_content = [
            "---",
            f"project: {self.discovery.project_path.name if self.discovery.project_path else 'Unknown'}",
            "purpose: Agent skills for this project",
            "type: agent-skills",
            "detected_type: agent",
            "confidence: 1.00",
            "version: 1.0",
            "---",
            "",
            "## PROJECT CONTEXT",
            "- **Type**: Agent",
            f"- **Domain**: Auto-generated skills index for {self.discovery.project_path.name if self.discovery.project_path else 'this project'}",
            "",
            "## SKILLS INDEX",
            ""
        ]

        # 4. Process each skill
        current_type = None
        for name, data in sorted_skills:
            # Add section header if type changes
            skill_type = data['type'].upper()
            if skill_type != current_type:
                index_content.append(f"### {skill_type} SKILLS")
                index_content.append("")
                current_type = skill_type

            # Parse content
            content = data.get('content', '')
            # If content is missing (failed load), try to read file
            if not content and 'path' in data:
                try:
                    content = Path(data['path']).read_text(encoding='utf-8')
                except Exception:
                    continue
            
            parsed = SkillParser.parse_skill_md(content, name)
            
            # Format using Mandatory Template
            skill_block = [
                f"#### {name}",
                f"{parsed['description']}",
                "",
                f"**Triggers:** {', '.join(parsed['triggers']) if parsed['triggers'] else 'N/A'}",
                f"**When to use:** {parsed['when_to_use']}" if parsed['when_to_use'] else None,
                f"**Tools:** {', '.join(parsed['tools'])}",
                f"**Command:** {parsed['command']}",
                f"**Input/Output:** {parsed['input_output']}",
                ""
            ]
            # Filter None values
            index_content.extend([line for line in skill_block if line is not None])

        # 5. Write to .clinerules/skills/index.md
        output_path = self.discovery.project_skills_root / "index.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(index_content), encoding="utf-8")
        
        return output_path

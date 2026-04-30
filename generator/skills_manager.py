from pathlib import Path
from typing import Dict, List, Optional, Set

from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator
from generator.skill_parser import SkillParser


class SkillsManager:
    """
    Facade for skill management.
    Delegates to SkillDiscovery, SkillParser, and SkillGenerator.
    """

    def __init__(self, project_path: Optional[Path] = None, skills_dir: Optional[Path] = None):
        """
        Initialize SkillsManager with Global and Project layers.

        Layers:
        1. Project (.clinerules/skills/project) - Metric overrides
        2. Global Learned (~/.project-rules-generator/learned) - User's shared skills
        3. Global Builtin (~/.project-rules-generator/builtin) - Core PRG skills
        """
        self.discovery = SkillDiscovery(project_path, skills_dir=skills_dir)
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
        strategy: Optional[str] = None,
        scope: str = "learned",
    ) -> Path:
        """Create a new skill in the requested scope.

        Args:
            force: If True, overwrite an existing skill. Default False (skip).
            strategy: Router strategy passed to AIStrategyRouter when use_ai=True.
                      One of "auto", "speed", "quality", or "provider:<name>".
                      None means direct provider mode (backward compat).
            scope: 'learned' (default), 'builtin', or 'project'.
        """
        result = self.generator.create_skill(
            name, from_readme, project_path, use_ai, provider, force=force, strategy=strategy, scope=scope
        )
        # DESIGN-4: Invalidate cache so list_skills() / resolve_skill() see the new skill.
        self.discovery.invalidate_cache()
        return result

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
        use_ai: bool = False,
        provider: str = "groq",
    ) -> List[str]:
        """Generate project-specific learned skills from README and tech stack."""
        return self.generator.generate_from_readme(
            readme_content,
            tech_stack,
            output_dir,
            project_name,
            project_path,
            use_ai=use_ai,
            provider=provider,
        )

    def get_all_skills_content(self) -> Dict[str, Dict]:
        """Get full content of all skills for export (Project > Learned > Builtin)."""
        return self.discovery.get_all_skills_content()

    def extract_all_triggers(self) -> Dict[str, List[str]]:
        """Extract auto-trigger phrases from all skills."""
        all_skills = self.discovery.get_all_skills_content()
        return SkillParser.extract_all_triggers(all_skills)

    def extract_project_triggers(self, include_only: Optional[Set[str]] = None) -> Dict[str, List[str]]:
        """Extract triggers from project and learned skills only.

        Excludes builtins — their triggers are generic and appear in rules.md
        even when unrelated to the actual project, which misleads users into
        thinking PRG generated project-specific skills when it didn't.

        Args:
            include_only: Optional set of skill references (e.g. {'learned/fastapi'})
                          to include. If None, all learned skills are included.
                          Project-local skills are always included.
        """
        all_skills = self.discovery.get_all_skills_content()

        project_only = {}
        # Always include project-local skills
        if "project" in all_skills:
            project_only["project"] = all_skills["project"]

        # Filter learned skills by include_only if provided
        if "learned" in all_skills:
            if include_only is not None:
                # Skill keys in all_skills['learned'] are the names, e.g. 'fastapi'
                # include_only set contains refs, e.g. 'learned/fastapi'
                learned_filtered = {
                    name: data for name, data in all_skills["learned"].items() if f"learned/{name}" in include_only
                }
                project_only["learned"] = learned_filtered
            else:
                project_only["learned"] = all_skills["learned"]

        return SkillParser.extract_all_triggers(project_only)

    def save_triggers_json(self, output_dir: Path, include_only: Optional[Set[str]] = None):
        """Save extracted triggers to .clinerules/auto-triggers.json

        Uses extract_project_triggers (project + filtered learned only) to avoid
        polluting auto-triggers.json with triggers from globally-available builtin
        skills that are unrelated to the current project.

        Args:
            include_only: Optional set of skill refs (e.g. {'learned/fastapi'}) to
                          include from the learned layer. Matches extract_project_triggers
                          semantics. If None, all learned skills are included.
        """
        triggers = self.extract_project_triggers(include_only=include_only)
        SkillParser.save_triggers_json(triggers, output_dir)

    def _extract_tech_context(self, tech: str, readme_content: str) -> List[str]:
        """Delegate to SkillParser."""
        return SkillParser.extract_tech_context(tech, readme_content)

    def _summarize_purpose(self, tech: str, context_lines: List[str], project_name: str) -> str:
        """Delegate to SkillParser."""
        return SkillParser.summarize_purpose(tech, context_lines, project_name)

    def _build_guidelines(self, tech: str, context_lines: list) -> str:
        """Delegate to SkillParser."""
        return SkillParser.build_guidelines(tech, context_lines)

    def generate_perfect_index(self, project_type: Optional[str] = None, include_only: Optional[Set[str]] = None):
        """
        Auto-generate .clinerules/skills/index.md from all available skills.
        Follows the Perfect Format: Name, Description, Triggers, When to use, Tools, Command, I/O.

        Args:
            project_type: Optional project type string (e.g. "python-api", "react-app").
                          When supplied, skills irrelevant to this type are excluded so
                          agents don't see e.g. React skills in a Python CLI project.
            include_only: Optional set of skill refs (e.g. {"builtin/code-review",
                          "project/gemini-api"}) to include. When supplied only those
                          skills are listed so index.md matches clinerules.yaml exactly.
                          Project-local skills are always included regardless.
        """
        from generator.skill_generator import SkillGenerator

        excluded: frozenset = SkillGenerator.PROJECT_TYPE_SKILL_EXCLUSIONS.get(project_type or "", frozenset())

        # 1. Get all skills
        all_skills = self.discovery.list_skills()

        # 2. Sort skills by type and then name for consistent output; apply exclusions
        # H4 fix: build a name-only lookup from include_only so that a skill
        # selected as "builtin/code-review" still matches when list_skills()
        # returns it as "learned/code-review" (learned layer shadows builtin).
        include_names: Optional[Set[str]] = None
        if include_only is not None:
            include_names = {ref.rsplit("/", 1)[-1] for ref in include_only}

        sorted_skills = []
        for name, data in all_skills.items():
            if name in excluded:
                continue
            skill_type = data.get("type", "")
            # Project-local skills are always shown — they were just generated
            # for this project and should always be visible in the index.
            if include_names is not None and skill_type != "project":
                if name not in include_names:
                    continue
            sorted_skills.append((name, data))
        sorted_skills.sort(key=lambda x: (x[1]["type"], x[0]))

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
            "",
        ]

        # 4. Process each skill
        current_type = None
        for name, data in sorted_skills:
            # Add section header if type changes
            skill_type = data["type"].upper()
            if skill_type != current_type:
                index_content.append(f"### {skill_type} SKILLS")
                index_content.append("")
                current_type = skill_type

            # Parse content
            content = data.get("content", "")
            # If content is missing (failed load), try to read file
            if not content and "path" in data:
                try:
                    content = Path(data["path"]).read_text(encoding="utf-8")
                except OSError:
                    continue

            parsed = SkillParser.parse_skill_md(content, name)

            # Format using Mandatory Template
            skill_block = [
                f"#### {name}",
                f"{parsed['description']}",
                "",
                f"**Triggers:** {', '.join(parsed['triggers']) if parsed['triggers'] else 'N/A'}",
                f"**When to use:** {parsed['when_to_use']}" if parsed["when_to_use"] else None,
                f"**Tools:** {', '.join(parsed['tools'])}",
                f"**Command:** {parsed['command']}",
                f"**Input/Output:** {parsed['input_output']}",
                "",
            ]
            # Filter None values
            index_content.extend([line for line in skill_block if line is not None])

        # 5. Write to .clinerules/skills/index.md
        if self.discovery.project_skills_root is None:
            return None
        output_path = self.discovery.project_skills_root / "index.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(index_content), encoding="utf-8")

        return output_path

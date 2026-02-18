import re
from pathlib import Path
from typing import Dict, List, Optional

from generator.skill_discovery import SkillDiscovery
from generator.skill_parser import SkillParser
from generator.skill_creator import CoworkSkillCreator
from generator.utils.quality_checker import is_stub as _check_is_stub
from generator.utils.tech_detector import extract_context as _extract_tech_context


class SkillGenerator:
    """Manages creation and generation of skills."""

    # Tech name → preferred skill filename
    TECH_SKILL_NAMES = {
        "fastapi": "fastapi-endpoints",
        "flask": "flask-routes",
        "django": "django-views",
        "express": "express-routes",
        "react": "react-components",
        "vue": "vue-components",
        "pytest": "pytest-testing",
        "jest": "jest-testing",
        "docker": "docker-deployment",
        "sqlalchemy": "sqlalchemy-models",
        "celery": "celery-tasks",
        "pydantic": "pydantic-validation",
        "click": "click-cli",
        "typer": "typer-cli",
        "websocket": "websocket-handler",
        "websockets": "websocket-handler",
        "graphql": "graphql-schema",
        "redis": "redis-caching",
        "mongodb": "mongodb-queries",
        "postgresql": "postgresql-queries",
        "pytorch": "pytorch-training",
        "tensorflow": "tensorflow-models",
        "openai": "openai-api",
        "anthropic": "anthropic-api",
        "groq": "groq-api",
        "gemini": "gemini-api",
        "perplexity": "perplexity-api",
        "langchain": "langchain-chains",
        "httpx": "httpx-client",
        "requests": "requests-client",
        "chrome": "chrome-extension",
        "chrome-extension": "chrome-extension",
        "gitpython": "gitpython-ops",
        "mcp": "mcp-protocol",
        "uvicorn": "uvicorn-server",
        "aiohttp": "aiohttp-client",
    }

    def __init__(self, discovery: SkillDiscovery):
        self.discovery = discovery

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
            name: Skill name (will be normalized to lowercase-hyphenated).
            from_readme: README content to use for context.
            project_path: Project path for CoworkStrategy.
            use_ai: Whether to use AI provider.
            provider: AI provider name ('groq' or 'gemini').
            force: If True, overwrite an existing skill. Default False (skip).

        Returns:
            Path to the skill directory.

        Raises:
            ValueError: If the skill name is invalid.
        """
        from generator.strategies import (
            AIStrategy,
            READMEStrategy,
            CoworkStrategy,
            StubStrategy,
        )

        self.discovery.ensure_global_structure()

        # Normalize name: lowercase, hyphens only
        safe_name = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
        if not safe_name:
            raise ValueError("Invalid skill name provided.")

        # ── Duplicate guard ──────────────────────────────────────────────────
        if self.discovery.skill_exists(safe_name, scope="learned") and not force:
            existing = self.discovery.resolve_skill(safe_name)
            print(f"⏭️  Skill '{safe_name}' already exists — skipping. (use force=True to overwrite)")
            return existing.parent if existing and existing.name == "SKILL.md" else existing.parent
        # ─────────────────────────────────────────────────────────────────────

        # Target is GLOBAL learned (directory format)
        target_dir = self.discovery.global_learned / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)

        skill_file = target_dir / "SKILL.md"

        # Strategy chain: try each strategy until one succeeds
        strategies = []
        if use_ai:
            strategies.append(AIStrategy())
        if from_readme:
            strategies.append(READMEStrategy())
        if project_path:
            strategies.append(CoworkStrategy())
        strategies.append(StubStrategy())  # Always available as final fallback

        content = None
        for strategy in strategies:
            content = strategy.generate(safe_name, project_path, from_readme, provider)
            if content:
                break

        skill_file.write_text(content, encoding="utf-8")
        return target_dir



    def generate_from_readme(
        self,
        readme_content: str,
        tech_stack: List[str],
        output_dir: Path,
        project_name: str = "",
        project_path: Optional[Path] = None,
    ) -> List[str]:
        """Generate project-specific learned skills from README and tech stack."""

        # Prefer the manager's project local dir if available, else derive from output_dir
        if self.discovery.project_local_dir:
            target_dir = self.discovery.project_local_dir
        else:
            # Fallback (e.g. if discovery wasn't init with project path but create_skill passed one?)
            target_dir = output_dir / "skills" / "project"

        target_dir.mkdir(parents=True, exist_ok=True)

        # Map tech to project-specific skill definitions
        skill_templates = self._derive_project_skills(
            tech_stack, readme_content, project_name
        )

        generated = []
        for skill_name, skill_content in skill_templates.items():
            dest = target_dir / f"{skill_name}.md"
            if dest.exists():
                # Overwrite if existing file is a generic stub or hallucinated
                if self._is_generic_stub(dest, project_path=project_path):
                    dest.write_text(skill_content, encoding="utf-8")
                    generated.append(skill_name)
            else:
                dest.write_text(skill_content, encoding="utf-8")
                generated.append(skill_name)

        return generated

    def _derive_project_skills(
        self,
        tech_stack: List[str],
        readme_content: str,
        project_name: str,
    ) -> Dict[str, str]:
        """Derive project-specific skill names and content from tech stack."""
        skills = {}
        seen_names = set()

        for tech in tech_stack:
            tech_lower = tech.lower().strip()
            skill_name = self.TECH_SKILL_NAMES.get(tech_lower)
            if not skill_name or skill_name in seen_names:
                continue
            seen_names.add(skill_name)

            # Extract README context for this specific tech using SkillParser
            context_lines = SkillParser.extract_tech_context(tech, readme_content)
            title = skill_name.replace("-", " ").title()

            purpose = SkillParser.summarize_purpose(tech, context_lines, project_name)
            triggers = SkillParser.build_triggers(tech, context_lines)
            guidelines = SkillParser.build_guidelines(tech, context_lines)

            content = f"# {title}\n\n"
            content += f"**Project:** {project_name or 'this project'}\n\n"
            content += f"## Purpose\n\n{purpose}\n\n"
            content += f"## Auto-Trigger\n\n{triggers}\n\n"
            content += f"## Guidelines\n\n{guidelines}\n"

            if context_lines:
                content += "\n## Project Context (from README)\n\n"
                for line in context_lines:
                    content += f"> {line}\n"

            skills[skill_name] = content

        return skills

    @staticmethod
    def _is_generic_stub(filepath: Path, project_path: Optional[Path] = None) -> bool:
        """Check if a skill file is a generic stub or contains hallucinations.
        
        Delegates to generator.utils.quality_checker.is_stub().
        Kept for backward compatibility.
        """
        return _check_is_stub(filepath, project_path)

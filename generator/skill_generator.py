import re
from pathlib import Path
from typing import Dict, List, Optional

from generator.skill_discovery import SkillDiscovery
from generator.skill_parser import SkillParser


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
    ) -> Path:
        """Create a new learned skill in the GLOBAL cache."""
        self.discovery.ensure_global_structure()

        # Sanitize name
        safe_name = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
        if not safe_name:
            raise ValueError("Invalid skill name provided.")

        # Target is GLOBAL learned
        target_dir = self.discovery.global_learned / safe_name
        if target_dir.exists():
            print(
                f"Skill '{safe_name}' already exists in global learned cache. Updating..."
            )
        else:
            target_dir.mkdir(parents=True, exist_ok=True)

        skill_file = target_dir / "SKILL.md"

        content = ""

        # 1. AI Generation
        if use_ai and project_path:
            try:
                from generator.llm_skill_generator import LLMSkillGenerator
                from generator.project_analyzer import ProjectAnalyzer

                print(f"🤖 Analyzing project context in {project_path}...")
                analyzer = ProjectAnalyzer(Path(project_path))
                context = analyzer.analyze()

                print("✨ Generating skill with AI...")
                generator = LLMSkillGenerator()
                content = generator.generate_skill(safe_name, context)
            except ImportError as e:
                print(
                    f"[!] Warning: AI provider not available ({e}). Falling back to standard parsing."
                )
            except Exception as e:
                print(
                    f"[!] Warning: AI generation failed ({e}). Falling back to standard parsing."
                )
                # Fallthrough

        # 2. Smart README Parsing (if AI didn't generate content)
        if not content and from_readme:
            readme_path = Path(from_readme)
            if readme_path.exists():
                try:
                    # Using imports from analyzer.readme_parser for legacy compatibility functions if needed,
                    # but prefer SkillParser logic where we extracted it.
                    # Actually, the original code imported from analyzer.readme_parser for:
                    # extract_purpose, extract_tech_stack, extract_auto_triggers, extract_process_steps, extract_anti_patterns
                    # Some of these are in SkillParser now, but some (process_steps, anti_patterns) might not be fully moved yet
                    # or I missed them in the refactoring list!

                    # Refactoring Check: I moved _summarize_purpose, _build_triggers.
                    # But create_skill used imports from `analyzer.readme_parser`.
                    # Let's see if I can delegate to SkillParser equivalents or if I need to use the analyzer ones?
                    # `_summarize_purpose` in SkillParser is slightly different from `extract_purpose`.
                    # Let's stick to using `analyzer.readme_parser` imports for `create_skill` where possible to minimize logic change,
                    # OR update to use `SkillParser` logic if it covers it.
                    # The `SkillParser` I wrote covers `extract_tech_context`, `summarize_purpose` (similar behavior), `build_triggers`.
                    # It DOES NOT cover `extract_process_steps` or `extract_anti_patterns` (those were not in SkillsManager private methods).

                    # So I should keep the imports from `analyzer.readme_parser` for those specific functions.
                    from analyzer.readme_parser import (
                        extract_anti_patterns,
                        extract_auto_triggers,
                        extract_process_steps,
                        extract_purpose,
                        extract_tech_stack,
                    )

                    readme_content = readme_path.read_text(
                        encoding="utf-8", errors="replace"
                    )

                    purpose = extract_purpose(readme_content)
                    tech = extract_tech_stack(readme_content)
                    triggers = extract_auto_triggers(readme_content, safe_name)
                    steps = extract_process_steps(readme_content)
                    anti_patterns = extract_anti_patterns(
                        readme_content, tech, project_path=readme_path.parent
                    )

                    # Build skill content
                    title = safe_name.replace("-", " ").title()
                    content = f"# Skill: {title}\n\n"
                    content += f"## Purpose\n{purpose}\n\n"

                    content += "## Auto-Trigger\n"
                    content += "\n".join(["- " + t for t in triggers]) + "\n\n"

                    content += "## Process\n\n"
                    step_count = 1
                    for step in steps:
                        if step.strip().startswith("```"):
                            content += f"{step}\n\n"
                        else:
                            clean_step = re.sub(r"^\d+\.\s*", "", step)
                            content += f"### {step_count}. {clean_step}\n\n"
                            step_count += 1

                    content += "## Output\n[Describe what artifacts or state changes result from following this skill]\n\n"

                    content += "## Anti-Patterns\n"
                    for ap in anti_patterns:
                        content += f"❌ {ap}\n"

                    if tech:
                        content += f"\n## Tech Stack\n{', '.join(tech)}\n"

                    content += (
                        f"\n## Context (from {readme_path.name})\n\n{readme_content}\n"
                    )

                except Exception as e:
                    print(
                        f"[!] Warning: Smart parsing failed ({e}). Falling back to template."
                    )
                    pass
            else:
                print(f"[!] Warning: README {from_readme} not found.")

        # 3. Fallback / Default Template if content not generated
        if not content:
            if from_readme and Path(from_readme).exists():
                readme_path = Path(from_readme)
                readme_content = readme_path.read_text(
                    encoding="utf-8", errors="replace"
                )
                additional_context = (
                    f"\n\n## Context (from {readme_path.name})\n\n{readme_content}\n"
                )
            else:
                additional_context = ""

            title = safe_name.replace("-", " ").title()
            content = f"# Skill: {title}\n\n## Purpose\n[One sentence: what problem does this solve]\n\n## Auto-Trigger\n[When should agent activate this skill]\n\n## Process\n[Step-by-step instructions]\n\n## Output\n[What artifact/state results]\n\n## Anti-Patterns\n[x] [What NOT to do]\n"
            content += additional_context

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
        """Check if a skill file is a generic stub or contains hallucinations."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return False

        # 1. Generic stub markers
        stub_markers = [
            "Follow project conventions",
            "Patterns and best practices for",
            "[One sentence: what problem does this solve]",
            "[When should agent activate this skill]",
            "[Step-by-step instructions]",
            "Working with general code",
            "Add tests for new functionality",
        ]
        if any(marker in content for marker in stub_markers):
            return True

        # 2. Hallucinated file path detection
        hallucinated_paths = re.findall(
            r"(?:File:\s*)?src/[\w/]+\.py(?::\d+)?", content
        )
        if hallucinated_paths and project_path:
            src_dir = project_path / "src"
            if not src_dir.exists():
                return True

        # 3. Detect fake file path patterns in code blocks
        file_refs = re.findall(r"#\s*File:\s*(\S+)", content)
        if file_refs and project_path:
            fake_count = 0
            for ref in file_refs:
                ref_path = ref.split(":")[0]
                full_path = project_path / ref_path
                if not full_path.exists():
                    fake_count += 1
            if fake_count > 0 and fake_count >= len(file_refs) / 2:
                return True

        return False

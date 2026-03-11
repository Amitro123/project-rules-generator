import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from generator.skill_discovery import SkillDiscovery
from generator.skill_parser import SkillParser
from generator.utils.quality_checker import is_stub as _check_is_stub


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
        # 2D/3D canvas & DXF editing
        "dxf": "dxf-processing",
        "konva": "konva-nesting-canvas",
        "canvas": "konva-nesting-canvas",
        "threejs": "threejs-scene",
        "babylon": "babylon-scene",
        "supabase": "supabase-auth-storage",
        "reportlab": "reportlab-pdf",
        "pdf": "reportlab-pdf",
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
        strategy: Optional[str] = None,
    ) -> Path:
        """Create a new learned skill in the GLOBAL cache.

        Args:
            name: Skill name (will be normalized to lowercase-hyphenated).
            from_readme: README content to use for context.
            project_path: Project path for CoworkStrategy.
            use_ai: Whether to use AI provider.
            provider: AI provider name ('groq', 'gemini', 'anthropic', 'openai').
            force: If True, overwrite an existing skill. Default False (skip).
            strategy: Router strategy ("auto", "speed", "quality", "provider:X").
                      None → direct provider mode.

        Returns:
            Path to the skill directory.

        Raises:
            ValueError: If the skill name is invalid.
        """
        from generator.strategies import AIStrategy, CoworkStrategy, READMEStrategy, StubStrategy

        self.discovery.ensure_global_structure()

        # Normalize name: lowercase, hyphens only
        safe_name = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
        if not safe_name:
            raise ValueError("Invalid skill name provided.")

        # ── Duplicate guard ──────────────────────────────────────────────────
        if self.discovery.skill_exists(safe_name, scope="learned") and not force:
            existing = self.discovery.resolve_skill(safe_name)
            print(f"Skill '{safe_name}' already exists — skipping. (use force=True to overwrite)")
            if existing is not None:
                # BUG-1 fix: for SKILL.md → return skill dir (existing.parent);
                # for flat file (fastapi-endpoints.md) → also return existing.parent
                # (the learned/ container), NOT parent / safe_name which doesn't exist.
                return existing.parent
            # Fallback: return the expected directory path
            return self.discovery.global_learned / safe_name
        # ─────────────────────────────────────────────────────────────────────

        # Target: prefer Local Learned if project context exists, else Global Learned
        if self.discovery.project_learned_link:
            target_root = self.discovery.project_learned_link
        else:
            target_root = self.discovery.global_learned

        target_dir = target_root / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)

        skill_file = target_dir / "SKILL.md"

        # Strategy chain: try each strategy until one succeeds
        strategies: List[Any] = []
        if use_ai:
            strategies.append(AIStrategy())

        # BUG-A fix: from_readme may be a file path (from CLI --from-readme) or
        # raw content (from generate_from_readme).  Normalise to content here so
        # every strategy in the chain receives the same contract.
        readme_content = from_readme
        if from_readme and Path(from_readme).is_file():
            readme_content = Path(from_readme).read_text(encoding="utf-8", errors="replace")

        if readme_content:
            strategies.append(READMEStrategy())
        if project_path:
            strategies.append(CoworkStrategy())
        strategies.append(StubStrategy())  # Always available as final fallback

        content = None
        for strategy_obj in strategies:
            content = strategy_obj.generate(safe_name, project_path, readme_content, provider, strategy=strategy)
            if content:
                break

        skill_file.write_text(content or "", encoding="utf-8")

        # GAP 3: Progressive disclosure — scaffold Level 3 subdirectories
        self._scaffold_level3(target_dir, safe_name)

        # DESIGN-1 fix: invalidate the cache so list_skills() / skill_exists() see
        # the newly-created skill immediately instead of stale pre-creation data.
        self.discovery.invalidate_cache()

        return target_dir

    @staticmethod
    def _scaffold_level3(skill_dir: Path, skill_name: str) -> None:
        """Create Level 3 progressive-disclosure subdirectories (GAP 3).

        Anthropic spec levels:
          Level 1 — YAML frontmatter (always in system prompt)
          Level 2 — SKILL.md body (loaded when skill is relevant)
          Level 3 — scripts/, references/, assets/ (on-demand navigation)
        """
        subdirs = {
            "scripts": (
                f"# {skill_name} — Scripts\n\n"
                "Place executable helper scripts here.\n"
                "Claude will read these on demand when it needs to run validations\n"
                "or generate code for this skill.\n\n"
                "Examples:\n"
                "- `validate.py` — verify the skill's output is correct\n"
                "- `generate.py` — code-generation helper\n"
            ),
            "references": (
                f"# {skill_name} — References\n\n"
                "Place on-demand reference documentation here.\n"
                "Claude will read these when it needs deeper context beyond SKILL.md.\n\n"
                "Examples:\n"
                "- `patterns.md` — detailed pattern catalogue\n"
                "- `api-reference.md` — API surface summary\n"
            ),
            "assets": (
                f"# {skill_name} — Assets\n\n"
                "Place reusable template files here.\n"
                "Claude will reference these when generating boilerplate for this skill.\n\n"
                "Examples:\n"
                "- `template.py.j2` — Jinja2 code template\n"
                "- `config.yaml.j2` — configuration template\n"
            ),
        }
        for dirname, readme_content in subdirs.items():
            subdir = skill_dir / dirname
            subdir.mkdir(exist_ok=True)
            readme = subdir / "README.md"
            if not readme.exists():
                readme.write_text(readme_content, encoding="utf-8")

    def check_global_skill_reuse(self, tech_stack: List[str]) -> Dict[str, str]:
        """Check which skills already exist in global learned for a given tech stack.

        Returns a dict of skill_name -> 'reuse' | 'adapt' | 'create'
        - 'reuse':  skill exists globally and content is rich (not a stub)
        - 'adapt':  skill exists globally but is a generic stub needing project adaptation
        - 'create': skill does not exist globally at all
        """
        result: Dict[str, str] = {}
        for tech in tech_stack:
            tech_lower = tech.lower().strip()
            skill_name = self.TECH_SKILL_NAMES.get(tech_lower)
            if not skill_name:
                continue
            if result.get(skill_name):
                continue  # already classified via another tech alias

            if self.discovery.skill_exists(skill_name, scope="learned"):
                resolved = self.discovery.resolve_skill(skill_name)
                if resolved and resolved.exists():
                    if self._is_generic_stub(resolved):
                        result[skill_name] = "adapt"
                    else:
                        result[skill_name] = "reuse"
                else:
                    result[skill_name] = "adapt"
            else:
                result[skill_name] = "create"

        return result

    def generate_from_readme(
        self,
        readme_content: str,
        tech_stack: List[str],
        output_dir: Path,
        project_name: str = "",
        project_path: Optional[Path] = None,
    ) -> List[str]:
        """Generate project-specific learned skills from README and tech stack.

        Cross-project reuse logic:
        - 'reuse': global skill is rich → symlink/copy it to project, don't regenerate
        - 'adapt': global skill is a stub → regenerate with project context
        - 'create': no global skill → create new one in global learned + reference it
        """
        if self.discovery.project_local_dir:
            target_dir = self.discovery.project_local_dir
        else:
            target_dir = output_dir / "skills" / "project"

        target_dir.mkdir(parents=True, exist_ok=True)

        # Classify skills: reuse / adapt / create
        reuse_map = self.check_global_skill_reuse(tech_stack)

        # Map tech to project-specific skill content (for adapt/create cases)
        skill_templates = self._derive_project_skills(tech_stack, readme_content, project_name)

        generated = []
        for skill_name, skill_content in skill_templates.items():
            action = reuse_map.get(skill_name, "create")
            dest = target_dir / f"{skill_name}.md"

            if action == "reuse":
                # Rich global skill exists — copy it to project dir as-is
                resolved = self.discovery.resolve_skill(skill_name)
                if resolved and resolved.exists():
                    shutil.copy2(resolved, dest)
                    print(f"  [reuse]  {skill_name} (from global learned)")
                    generated.append(f"{skill_name} (reused)")
                    continue
                # BUG-4 fix: resolve_skill returned None (stale cache or file deleted).
                # Log a warning and fall through to the create path so the skill
                # is not silently lost. We use a second `if` below (not elif) so that
                # the reassigned action='create' is actually evaluated.
                print(f"  [warn]  {skill_name}: cached skill not found, falling through to create")
                action = "create"

            if action == "adapt":
                # Stub exists globally — write project-adapted version to project dir ONLY.
                # BUG-B fix: Do NOT write project-specific content back to the global
                # learned cache — that would pollute it with project-name, project-specific
                # triggers, and README context that don't apply to other projects.
                dest.write_text(skill_content, encoding="utf-8")
                print(f"  [adapt]  {skill_name} (project override)")
                generated.append(f"{skill_name} (adapted)")

            elif action == "create":
                # No global skill — write to project dir and save to global learned
                dest.write_text(skill_content, encoding="utf-8")
                global_dest = self.discovery.global_learned / f"{skill_name}.md"
                if not global_dest.exists():
                    global_dest.write_text(skill_content, encoding="utf-8")
                    print(f"  [create] {skill_name} (saved to global learned)")
                else:
                    print(f"  [create] {skill_name} (project copy only)")
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

            # GAP 1: prepend Anthropic-spec-compliant YAML frontmatter
            fm_triggers = [tech, f"add {tech}", f"implement {tech}", skill_name.replace("-", " ")]
            trigger_str = ", ".join(f'"{t}"' for t in fm_triggers)
            fm_desc = f"{purpose.rstrip('.')}. Use when user mentions {trigger_str}."[:1024]
            fm_tags = list(dict.fromkeys([p for p in skill_name.split("-") if len(p) > 2] + [tech.lower()]))[:5]
            fm_tags_str = "[" + ", ".join(fm_tags) + "]"
            content = (
                f"---\n"
                f"name: {skill_name}\n"
                f"description: |\n"
                f"  {fm_desc}\n"
                f"license: MIT\n"
                f'allowed-tools: "Bash Read Write Edit Glob Grep"\n'
                f"metadata:\n"
                f"  author: PRG\n"
                f"  version: 1.0.0\n"
                f"  category: project\n"
                f"  tags: {fm_tags_str}\n"
                f"---\n\n"
            )
            content += f"# {title}\n\n"
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

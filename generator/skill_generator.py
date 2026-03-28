import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

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
        "anthropic": "claude-cowork-workflow",
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

        # Target: prefer Local Learned if project context exists AND the dir is on disk
        # (BUG-2 fix: Path object is always truthy; must also check .exists())
        if self.discovery.project_learned_link and self.discovery.project_learned_link.exists():
            target_root = self.discovery.project_learned_link
        else:
            target_root = self.discovery.global_learned

        target_dir = target_root / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)

        skill_file = target_dir / "SKILL.md"

        content = self._run_strategy_chain(
            safe_name, from_readme, project_path, use_ai=use_ai, provider=provider, strategy=strategy
        )
        skill_file.write_text(content or "", encoding="utf-8")

        # DESIGN-1 fix: invalidate the cache so list_skills() / skill_exists() see
        # the newly-created skill immediately instead of stale pre-creation data.
        self.discovery.invalidate_cache()

        return target_dir

    def _run_strategy_chain(
        self,
        safe_name: str,
        from_readme: Optional[str],
        project_path: Optional[str],
        use_ai: bool = False,
        provider: str = "groq",
        strategy: Optional[str] = None,
    ) -> Optional[str]:
        """Run the strategy chain and return generated content without writing to disk.

        BUG-A fix: from_readme may be a file path (from CLI --from-readme) or
        raw content. Normalise to content so every strategy receives the same contract.
        """
        from generator.strategies import AIStrategy, CoworkStrategy, READMEStrategy, StubStrategy

        strategies: List[Any] = []
        if use_ai:
            strategies.append(AIStrategy())

        readme_content = from_readme
        if from_readme:
            # Guard against OSError ENAMETOOLONG (errno 36) when from_readme is already
            # raw content — Path.is_file() fails if the string is longer than 255 chars.
            try:
                p = Path(from_readme)
                if p.is_file():
                    readme_content = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass  # from_readme is content, not a path — use as-is

        if readme_content:
            strategies.append(READMEStrategy())
        if project_path:
            strategies.append(CoworkStrategy())
        strategies.append(StubStrategy())  # Always available as final fallback

        # CoworkStrategy is a project-context enrichment layer — it should NOT
        # re-run AI when AIStrategy is already the primary AI path in this chain.
        # Only forward use_ai=True to CoworkStrategy when AIStrategy was NOT added
        # (i.e. use_ai=False, or project-path-only mode with no readme).
        cowork_use_ai = use_ai and not any(isinstance(s, AIStrategy) for s in strategies)

        for strategy_obj in strategies:
            try:
                if isinstance(strategy_obj, CoworkStrategy):
                    content = strategy_obj.generate(safe_name, project_path, readme_content, provider, strategy=strategy, use_ai=cowork_use_ai)
                else:
                    content = strategy_obj.generate(safe_name, project_path, readme_content, provider, strategy=strategy, use_ai=use_ai)
                if content:
                    return content
            except Exception as exc:
                logger.warning(
                    "Strategy %s failed, trying next: %s",
                    strategy_obj.__class__.__name__,
                    exc,
                )
        return None

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

        # Deduplicated list of skill names in tech_stack order
        seen_names: set = set()
        skill_names = []
        for tech in tech_stack:
            skill_name = self.TECH_SKILL_NAMES.get(tech.lower().strip())
            if skill_name and skill_name not in seen_names:
                seen_names.add(skill_name)
                skill_names.append(skill_name)

        generated = []
        project_path_str = str(project_path) if project_path else None
        for skill_name in skill_names:
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

            # Delegate to _run_strategy_chain() so adapt/create cases go through the
            # full strategy chain (CoworkStrategy, quality validation, etc.).
            skill_content = self._run_strategy_chain(
                skill_name,
                from_readme=readme_content,
                project_path=project_path_str,
            )

            if action == "adapt":
                # Stub exists globally — write project-adapted version to project dir ONLY.
                # BUG-B fix: Do NOT write project-specific content back to the global
                # learned cache — that would pollute it with project-name, project-specific
                # triggers, and README context that don't apply to other projects.
                dest.write_text(skill_content or "", encoding="utf-8")
                print(f"  [adapt]  {skill_name} (project override)")
                generated.append(f"{skill_name} (adapted)")

            elif action == "create":
                # No global skill — write to project dir and save to global learned
                dest.write_text(skill_content or "", encoding="utf-8")
                global_dest = self.discovery.global_learned / f"{skill_name}.md"
                if not global_dest.exists():
                    global_dest.write_text(skill_content or "", encoding="utf-8")
                    print(f"  [create] {skill_name} (saved to global learned)")
                else:
                    print(f"  [create] {skill_name} (project copy only)")
                generated.append(skill_name)

        return generated

    @staticmethod
    def _is_generic_stub(filepath: Path, project_path: Optional[Path] = None) -> bool:
        """Check if a skill file is a generic stub or contains hallucinations.

        Delegates to generator.utils.quality_checker.is_stub().
        Kept for backward compatibility.
        """
        return _check_is_stub(filepath, project_path)

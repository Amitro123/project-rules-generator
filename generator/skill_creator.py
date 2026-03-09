"""
Cowork-Powered Skill Creator
===========================

This module implements Cowork's intelligent skill creation logic for PRG.
It generates high-quality, project-specific skills with:
- Smart auto-trigger optimization
- Intelligent tool selection
- Quality gates and validation
- Hallucination prevention
- Actionable, specific steps
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from generator.skill_discovery import SkillDiscovery
from generator.utils.quality_checker import QualityReport
from generator.utils.tech_detector import detect_from_dependencies as _detect_from_deps_util
from generator.utils.tech_detector import detect_tech_stack as _detect_tech_stack_util

try:
    from jinja2 import Environment, FileSystemLoader

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


@dataclass
class SkillMetadata:
    """Structured metadata for skill generation."""

    name: str
    description: str
    auto_triggers: List[str] = field(default_factory=list)
    project_signals: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    category: str = "project"
    priority: int = 50  # 0-100, higher = more priority
    negative_triggers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class CoworkSkillCreator:
    """
    Generates Cowork-quality skills for PRG projects.

    This creator combines:
    - Cowork's trigger optimization intelligence
    - Smart tool selection based on tech stack
    - Quality gates for actionability
    - Hallucination detection
    """

    # Technology → Required Tools mapping (Cowork intelligence)
    TECH_TOOLS = {
        "fastapi": ["uvicorn", "pydantic", "pytest", "httpx"],
        "flask": ["flask", "pytest", "requests"],
        "django": ["django", "pytest", "django-admin"],
        "react": ["npm", "webpack", "jest", "eslint"],
        "vue": ["npm", "vue-cli", "jest"],
        "pytest": ["pytest", "coverage", "pytest-cov"],
        "qa": ["pytest", "coverage", "ruff", "vulture"],
        "docker": ["docker", "docker-compose"],
        "kubernetes": ["kubectl", "helm"],
        "sqlalchemy": ["alembic", "pytest"],
        "celery": ["redis-cli", "celery"],
        "redis": ["redis-cli"],
        "postgresql": ["psql", "pg_dump"],
        "mongodb": ["mongosh", "mongodump"],
        "git": ["git"],
        "github": ["gh"],
        "openai": ["openai"],
        "anthropic": ["anthropic"],
        "langchain": ["langchain"],
    }

    # Common trigger patterns (Cowork-style synonyms)
    TRIGGER_SYNONYMS = {
        "test": ["test", "testing", "unit test", "integration test", "verify"],
        "deploy": ["deploy", "deployment", "ship", "release", "publish"],
        "api": ["api", "endpoint", "route", "rest api", "graphql"],
        "database": ["database", "db", "schema", "migration", "query"],
        "debug": ["debug", "troubleshoot", "investigate", "diagnose"],
        "optimize": ["optimize", "improve", "enhance", "speed up", "performance"],
        "security": ["security", "secure", "audit", "vulnerability", "pentest"],
        "docs": ["documentation", "docs", "readme", "guide", "tutorial"],
        "refactor": ["refactor", "cleanup", "improve code", "reorganize"],
    }

    # Project signal detection (from file/folder structure)
    PROJECT_SIGNALS = {
        "has_docker": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
        "has_tests": ["tests/", "test/", "pytest.ini", "conftest.py"],
        "has_ci": [".github/workflows/", ".gitlab-ci.yml", ".circleci/"],
        "has_docs": ["docs/", "README.md", "CONTRIBUTING.md"],
        "has_api": ["api/", "routes/", "endpoints/", "app.py", "main.py"],
        "has_frontend": ["frontend/", "src/components/", "public/"],
        "has_database": ["migrations/", "alembic/", "models.py", "schema.sql"],
        "monorepo": ["packages/", "apps/", "workspaces"],
    }

    def __init__(self, project_path: Path):
        """Initialize with project path for context awareness."""
        self.project_path = project_path
        self._detected_signals: Optional[Set[str]] = None
        self._tech_stack: Optional[Set[str]] = None
        self.discovery = SkillDiscovery(project_path)

    def generate_all(self, project_path: Optional[Path] = None, use_ai: bool = False, provider: str = "gemini"):
        """
        GLOBAL LEARNED LIBRARY Flow (User's Vision!):
        1. Detect skill needs (e.g. pytest-testing-workflow)
        2. Check GLOBAL learned/
        3. Exists -> ♻️ Reuse (Link to project)
        4. Not exists -> ✨ Create (Cowork) -> Save to GLOBAL learned/ -> Link
        """
        proj_path = project_path or self.project_path

        # Ensure global structure and local project structure
        self.discovery.ensure_global_structure()
        self.discovery.setup_project_structure()

        # Get README for context
        readme_path = proj_path / "README.md"
        readme_content = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path.exists() else ""

        # 1. Detect needed skills
        needed_skills = self.detect_skill_needs(proj_path)
        print(f"🔍 Detected Needs: {needed_skills if needed_skills else ['None']}")

        if not needed_skills:
            return

        created = 0
        reused = 0

        # 2. Process each skill
        for skill_name in needed_skills:
            # Check GLOBAL learned
            if self.exists_in_learned(skill_name):
                print(f"♻️  Reusing: {skill_name}")
                self.link_from_learned(skill_name)
                reused += 1
                continue

            # Create NEW with Cowork quality
            print(f"\n{'=' * 60}")
            print(f"✨ Creating: {skill_name}")
            print(f"{'=' * 60}\n")

            try:
                # We need to determine the main tech for this skill to pass to create_skill
                # detect_skill_needs derives names like 'pytest-testing-workflow'
                # extraction: 'pytest' from 'pytest-testing-workflow'
                tech_hint = skill_name.split("-")[0]
                tech_stack_hint = [tech_hint] if tech_hint else None

                content, metadata, quality = self.create_skill(
                    skill_name, readme_content, tech_stack=tech_stack_hint, use_ai=use_ai, provider=provider
                )

                print(f"📊 Quality: {quality.score:.1f}/100")
                if not quality.passed and quality.issues:
                    print(f"Issues: {', '.join(quality.issues[:2])}")

                # Save to GLOBAL learned
                self.save_to_learned(skill_name, content)

                # Link to project
                self.link_from_learned(skill_name)

                print(f"💾 Saved to: ~/.project-rules-generator/learned/{skill_name}.md")
                print(f"🔗 Linked to: .clinerules/skills/project/{skill_name}.md")
                print(f"⚡ Triggers: {len(metadata.auto_triggers)} | Tools: {len(metadata.tools)}")

                created += 1

            except Exception as e:
                print(f"❌ Failed to create {skill_name}: {e}")
                import traceback

                traceback.print_exc()
                continue

        print(f"\n{'=' * 60}")
        print(f"⚡ Summary: ✨ Created: {created} | ♻️  Reused: {reused}")
        print(f"{'=' * 60}")

    def detect_skill_needs(self, project_path: Path) -> List[str]:
        """Detect needed skills based on tech stack and context.

        Uses SkillGenerator.TECH_SKILL_NAMES as the single source of truth for
        the tech→skill mapping (covers 40+ technologies).
        """
        # Lazy import to avoid circular dependency
        # (skill_generator → strategies → cowork_strategy → skill_creator)
        from generator.skill_generator import SkillGenerator

        readme_path = project_path / "README.md"
        readme_content = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path.exists() else ""

        tech_stack = self._detect_tech_stack(readme_content)
        skill_names = []

        if not tech_stack:
            skill_names.append(f"{project_path.name}-workflow")
        else:
            for tech in tech_stack:
                skill_name = SkillGenerator.TECH_SKILL_NAMES.get(tech.lower())
                if skill_name:
                    skill_names.append(skill_name)

            # If nothing matched, fall back to a generic project workflow
            if not skill_names:
                skill_names.append(f"{project_path.name}-workflow")

        return list(set(skill_names))

    def exists_in_learned(self, skill_name: str) -> bool:
        """Check if skill exists in global learned cache.

        Delegates to SkillDiscovery.skill_exists() — single source of truth.
        Checks both flat file (<name>.md) and directory (<name>/SKILL.md) formats.
        """
        return self.discovery.skill_exists(skill_name, scope="learned")

    def save_to_learned(self, skill_name: str, content: str):
        """Save skill to global learned cache."""
        # We prefer flat files for simplicity unless it needs resources, but
        # Cowork flow often uses directories?
        # Let's use flat .md for now as per previous patterns, or match existing.
        # implementation_plan said "global/learned/"

        target = self.discovery.global_learned / f"{skill_name}.md"
        target.write_text(content, encoding="utf-8")

    def link_from_learned(self, skill_name: str):
        """Link a learned skill from Global Cache to Project Local Skills."""
        # Source: ~/.project-rules-generator/learned/<skill_name>.md
        # Target: <project>/.clinerules/skills/project/<skill_name>.md

        source = self.discovery.global_learned / f"{skill_name}.md"
        if not source.exists():
            # Directory-style skill: <name>/SKILL.md
            source_dir = self.discovery.global_learned / skill_name
            if source_dir.exists() and source_dir.is_dir():
                source = source_dir / "SKILL.md"

        if not self.discovery.project_local_dir:
            print(f"⚠️  Could not link {skill_name}: No project path configured.")
            return

        target = self.discovery.project_local_dir / f"{skill_name}.md"

        if source.exists():
            self.discovery._link_or_copy(source, target)
        else:
            print(f"⚠️  Could not link {skill_name}: Source not found in global learned.")

    def setup_symlinks(self):
        """Ensure project symlinks are set up."""
        self.discovery.setup_project_structure()

    def create_skill(
        self,
        skill_name: str,
        readme_content: str,
        tech_stack: Optional[List[str]] = None,
        custom_context: Optional[Dict] = None,
        use_ai: bool = False,
        provider: str = "gemini",
    ) -> Tuple[str, SkillMetadata, QualityReport]:
        """
        Create a Cowork-quality skill with full intelligence.

        Args:
            skill_name: Name of skill (e.g., "fastapi-security-auditor")
            readme_content: Project README content for context
            tech_stack: Technologies used (auto-detected if None)
            custom_context: Additional context (file samples, etc.)

        Returns:
            Tuple of (skill_content, metadata, quality_report)
        """
        # 0. CRITICAL: Analyze ACTUAL project files first!
        project_analysis = self._analyze_project_structure(skill_name, tech_stack)

        # Merge with custom context
        if custom_context is None:
            custom_context = {}
        custom_context["project_analysis"] = project_analysis

        # 1. Build metadata with smart triggers
        metadata = self._build_metadata(skill_name, readme_content, tech_stack)

        # 2. Generate skill content (WITH actual project context!)
        content = self._generate_content(skill_name, readme_content, metadata, custom_context, use_ai, provider)

        # 3. Quality validation (will catch hallucinated paths!)
        quality = self._validate_quality(content, metadata)

        # 4. If quality is low, attempt auto-fix
        if not quality.passed:
            content = self._auto_fix_quality_issues(content, quality)
            quality = self._validate_quality(content, metadata)

        return content, metadata, quality

    def _analyze_project_structure(self, skill_name: str, tech_stack: Optional[List[str]]) -> Dict:
        """
        Analyze ACTUAL project structure - NO HALLUCINATIONS!

        This is critical for project-specific skills.
        """
        analysis: Dict[str, Any] = {
            "actual_files": [],
            "patterns": [],
            "structure": {},
        }

        # Detect skill type
        skill_lower = skill_name.lower()

        if "pytest" in skill_lower or "test" in skill_lower:
            # Analyze test structure
            test_dirs = []
            conftest_files = []
            test_files = []

            for test_dir in ["tests", "test"]:
                test_path = self.project_path / test_dir
                if test_path.exists():
                    test_dirs.append(str(test_path.relative_to(self.project_path)))

                    # Find actual files
                    if test_path.is_dir():
                        conftest = test_path / "conftest.py"
                        if conftest.exists():
                            conftest_files.append(str(conftest.relative_to(self.project_path)))

                        # Find test files
                        for test_file in test_path.glob("test_*.py"):
                            test_files.append(str(test_file.relative_to(self.project_path)))

            # Check for pytest.ini
            pytest_ini = self.project_path / "pytest.ini"
            if pytest_ini.exists():
                analysis["actual_files"].append("pytest.ini")

            analysis["structure"] = {
                "test_dirs": test_dirs,
                "conftest_files": conftest_files,
                "test_files": test_files[:5],  # Sample of 5
            }

            # Extract patterns from actual conftest.py
            if conftest_files:
                try:
                    conftest_content = (self.project_path / conftest_files[0]).read_text(
                        encoding="utf-8", errors="ignore"
                    )
                    if "pytest.fixture" in conftest_content:
                        analysis["patterns"].append("Uses pytest fixtures")
                    if "@pytest.mark" in conftest_content:
                        analysis["patterns"].append("Uses pytest markers")
                    if "pytest_configure" in conftest_content:
                        analysis["patterns"].append("Has pytest_configure hook")
                except Exception:
                    pass

        elif "fastapi" in skill_lower or "api" in skill_lower:
            # Analyze API structure
            api_files = []
            for api_dir in ["api", "app", "src"]:
                api_path = self.project_path / api_dir
                if api_path.exists() and api_path.is_dir():
                    for py_file in api_path.rglob("*.py"):
                        api_files.append(str(py_file.relative_to(self.project_path)))

            analysis["structure"]["api_files"] = api_files[:10]  # Sample

        return analysis

    def _build_metadata(
        self,
        skill_name: str,
        readme_content: str,
        tech_stack: Optional[List[str]] = None,
    ) -> SkillMetadata:
        """Build smart metadata with Cowork intelligence."""

        # Extract tech from name and README
        if tech_stack is None:
            tech_stack = self._detect_tech_stack(readme_content)

        # Generate smart triggers with synonyms
        triggers = self._generate_triggers(skill_name, readme_content, tech_stack)

        # Detect project signals
        signals = self._detect_project_signals()

        # Select tools intelligently
        tools = self._select_tools(skill_name, tech_stack)

        # Generate description
        description = self._generate_description(skill_name, readme_content)

        # GAP 5: negative triggers prevent over-activation
        negative_triggers = self._generate_negative_triggers(skill_name, tech_stack)

        # GAP 8: tags for search/filter
        tags = self._generate_tags(skill_name, tech_stack)

        return SkillMetadata(
            name=skill_name,
            description=description,
            auto_triggers=triggers,
            project_signals=list(signals),
            tools=tools,
            negative_triggers=negative_triggers,
            tags=tags,
        )

    def _generate_triggers(self, skill_name: str, readme_content: str, tech_stack: List[str]) -> List[str]:
        """
        Generate smart auto-triggers with Cowork-style variations.

        This is one of Cowork's key intelligences: creating multiple
        natural ways to invoke a skill.
        """
        triggers = []

        # 1. Base trigger from skill name
        base = skill_name.replace("-", " ").lower()
        triggers.append(base)

        # 2. Add tech-specific triggers
        for tech in tech_stack:
            tech_lower = tech.lower()
            if tech_lower in base:
                # "fastapi security" Γזע "audit fastapi", "review api security"
                triggers.append(f"audit {tech_lower}")
                triggers.append(f"review {tech_lower}")

        # 3. Expand with synonyms (Cowork magic!)
        expanded = set(triggers)
        for trigger in triggers:
            words = trigger.split()
            for word in words:
                if word in self.TRIGGER_SYNONYMS:
                    for synonym in self.TRIGGER_SYNONYMS[word][:2]:  # Top 2
                        new_trigger = trigger.replace(word, synonym)
                        expanded.add(new_trigger)

        # 4. Add action-based triggers from README context
        action_triggers = self._extract_action_triggers(readme_content, base)
        expanded.update(action_triggers)

        # Deduplicate and limit to top 8 most relevant
        return list(sorted(expanded))[:8]

    def _extract_action_triggers(self, readme_content: str, skill_base: str) -> Set[str]:
        """Extract action-based triggers from README."""
        triggers = set()

        # Look for imperative verbs near skill topic
        action_verbs = [
            "run",
            "execute",
            "check",
            "validate",
            "analyze",
            "generate",
            "create",
            "build",
            "test",
            "deploy",
        ]

        # Simple pattern matching
        lines = readme_content.lower().split("\n")
        skill_words = skill_base.split()

        for line in lines:
            # If line mentions skill-related words
            if any(word in line for word in skill_words):
                for verb in action_verbs:
                    if verb in line:
                        # "run security audit" Γזע "security audit"
                        triggers.add(f"{verb} {skill_base}")
                        break

        return triggers

    def _select_tools(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """
        Intelligently select tools needed for this skill.

        Cowork knows which tools are required for each tech stack.
        """
        tools = set()

        # 1. Tools from tech stack
        for tech in tech_stack:
            tech_lower = tech.lower()
            if tech_lower in self.TECH_TOOLS:
                tools.update(self.TECH_TOOLS[tech_lower])

        # 2. Common tools for skill type
        skill_lower = skill_name.lower()

        if "test" in skill_lower or "pytest" in skill_lower:
            tools.update(["pytest", "coverage", "tox"])

        if "deploy" in skill_lower or "docker" in skill_lower:
            tools.update(["docker", "docker-compose"])

        if "api" in skill_lower or "endpoint" in skill_lower or "fastapi" in skill_lower:
            tools.update(["curl", "httpx", "pytest", "uvicorn"])

        if "security" in skill_lower or "audit" in skill_lower:
            tools.update(["bandit", "safety", "ruff"])

        if "duplication" in skill_lower or "duplicate" in skill_lower or "dry" in skill_lower:
            tools.update(["pylint", "radon", "vulture"])

        if "refactor" in skill_lower or "cleanup" in skill_lower:
            tools.update(["pylint", "ruff", "black"])

        if "qa" in skill_lower or "bugs" in skill_lower:
            tools.update(["pytest", "ruff", "vulture", "mypy"])

        # 3. Validate tools exist in project
        tools = self._validate_tools_availability(tools)

        return list(sorted(tools))

    def _validate_tools_availability(self, tools: Set[str]) -> Set[str]:
        """Check if tools are actually available/referenced in project."""
        available = set()

        # Check requirements.txt, pyproject.toml, package.json
        requirement_files = [
            self.project_path / "requirements.txt",
            self.project_path / "pyproject.toml",
            self.project_path / "package.json",
        ]

        all_content = ""
        for req_file in requirement_files:
            if req_file.exists():
                try:
                    all_content += req_file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

        # Common Python/Node tools that are always available
        system_tools = {
            "git",
            "docker",
            "curl",
            "bash",
            "pytest",
            "python",
            "pip",
            "npm",
            "node",
            "pylint",
            "ruff",
            "black",
            "mypy",
            "coverage",
            "radon",
            "vulture",
            "bandit",
            "safety",
        }

        for tool in tools:
            # Tool exists in requirements OR is a common system/Python tool
            if tool in all_content or tool in system_tools:
                available.add(tool)

        return available

    def _detect_tech_stack(self, readme_content: str) -> List[str]:
        """
        Auto-detect tech stack from README AND actual project files.
        Delegates to generator.utils.tech_detector.detect_tech_stack().
        """
        if self._tech_stack:
            return list(self._tech_stack)
        detected = set(_detect_tech_stack_util(self.project_path, readme_content))
        self._tech_stack = detected
        return list(detected)

    def _detect_from_dependencies(self) -> Set[str]:
        """Detect tech from actual dependency files.
        Delegates to generator.utils.tech_detector.detect_from_dependencies().
        """
        return _detect_from_deps_util(self.project_path)

    def _detect_from_files(self) -> Set[str]:
        """Detect tech from actual project files."""
        detected = set()

        # Check for specific file types
        # React/Vue: .jsx, .tsx files
        if any(self.project_path.rglob("*.jsx")) or any(self.project_path.rglob("*.tsx")):
            detected.add("react")
            if any(self.project_path.rglob("*.tsx")):
                detected.add("typescript")

        if any(self.project_path.rglob("*.vue")):
            detected.add("vue")

        # Python files
        if any(self.project_path.rglob("*.py")):
            detected.add("python")

        # Tests
        if (self.project_path / "tests").exists() or (self.project_path / "test").exists():
            if detected.intersection({"python", "fastapi", "flask", "django"}):
                detected.add("pytest")
            if detected.intersection({"react", "vue", "javascript"}):
                detected.add("jest")

        return detected

    def _detect_from_readme(self, readme_content: str) -> Set[str]:
        """Detect tech from README (least reliable - use only for confirmation)."""
        tech_keywords = {
            "fastapi",
            "flask",
            "django",
            "express",
            "react",
            "vue",
            "pytest",
            "jest",
            "docker",
            "kubernetes",
            "postgresql",
            "mongodb",
            "redis",
            "celery",
            "sqlalchemy",
            "pydantic",
            "openai",
            "anthropic",
            "langchain",
            "typescript",
            "python",
        }

        # Look for tech in structured sections (more reliable)
        detected = set()

        # Try to find "Tech Stack" or "Built With" sections
        lines = readme_content.split("\n")
        in_tech_section = False

        for line in lines:
            line_lower = line.lower()

            # Check if entering tech section
            if any(marker in line_lower for marker in ["tech stack", "built with", "technologies", "dependencies"]):
                in_tech_section = True
                continue

            # Exit section if we hit a new header
            if line.strip().startswith("#") and in_tech_section:
                in_tech_section = False

            # If in tech section, be more lenient
            if in_tech_section:
                for tech in tech_keywords:
                    if tech in line_lower:
                        detected.add(tech)
            else:
                # Outside tech section, only detect if it's in a bullet point or strong emphasis
                if line.strip().startswith("-") or line.strip().startswith("*"):
                    for tech in tech_keywords:
                        if tech in line_lower:
                            detected.add(tech)

        return detected

    def _detect_project_signals(self) -> Set[str]:
        """Detect project structure signals (has_docker, has_tests, etc.)."""
        if self._detected_signals:
            return self._detected_signals

        signals = set()

        for signal_name, indicators in self.PROJECT_SIGNALS.items():
            for indicator in indicators:
                check_path = self.project_path / indicator
                if check_path.exists():
                    signals.add(signal_name)
                    break

        self._detected_signals = signals
        return signals

    README_MIN_WORDS = 80  # Below this → README is too sparse to rely on alone

    def is_readme_sufficient(self, readme_content: str) -> bool:
        """Return True if README has enough content for meaningful skill generation."""
        if not readme_content or not readme_content.strip():
            return False
        return len(readme_content.split()) >= self.README_MIN_WORDS

    def _scan_project_tree(self, max_depth: int = 3, max_items: int = 60) -> str:
        """Walk the project directory and produce a structured tree for LLM context.

        Excludes noise directories (.git, __pycache__, venv, node_modules, etc.).
        Capped at max_items entries to stay within token budget.
        """
        EXCLUDE = {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            "dist",
            "build",
            ".mypy_cache",
            ".ruff_cache",
            ".clinerules",
            ".claude",
            ".eggs",
            "eggs",
        }

        lines: List[str] = [f"{self.project_path.name}/"]
        count = 0

        def _walk(path: Path, depth: int, prefix: str) -> None:
            nonlocal count
            if depth > max_depth or count >= max_items:
                return
            try:
                entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            except PermissionError:
                return

            visible = [e for e in entries if not e.name.startswith(".") and e.name not in EXCLUDE]
            for i, item in enumerate(visible):
                if count >= max_items:
                    lines.append(f"{prefix}... (truncated)")
                    return
                connector = "└── " if i == len(visible) - 1 else "├── "
                child_prefix = prefix + ("    " if i == len(visible) - 1 else "│   ")
                if item.is_dir():
                    lines.append(f"{prefix}{connector}{item.name}/")
                    count += 1
                    _walk(item, depth + 1, child_prefix)
                else:
                    lines.append(f"{prefix}{connector}{item.name}")
                    count += 1

        _walk(self.project_path, 1, "")
        return "\n".join(lines)

    def _generate_description(self, skill_name: str, readme_content: str) -> str:
        """Generate concise skill description."""
        # Extract purpose from first paragraph mentioning skill topic
        skill_words = skill_name.replace("-", " ").split()

        lines = readme_content.split("\n")
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in skill_words) and len(line) > 20:
                # Found relevant line
                return line.strip()[:150]

        # Fallback: generic but specific
        tech_part = skill_name.split("-")[0].upper() if "-" in skill_name else ""
        action_part = skill_name.split("-")[-1] if "-" in skill_name else "workflow"
        return f"{tech_part} {action_part} for this project"

    def _generate_negative_triggers(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Generate negative triggers to prevent over-activation (GAP 5)."""
        negatives: List[str] = []
        tech = skill_name.split("-")[0].lower()

        # Generic queries that shouldn't activate a specific-tech skill
        if tech and tech not in ("project", "workflow"):
            negatives.append(f"general {tech} questions")
            negatives.append(f"{tech} theory")

        # If skill is about testing, don't activate on production topics
        if "test" in skill_name:
            negatives.append("production deployment")
        # If skill is about deployment, don't activate on writing tests
        if "deploy" in skill_name or "docker" in skill_name:
            negatives.append("writing unit tests")

        return negatives[:3]  # cap at 3 per spec recommendation

    def _generate_tags(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Derive searchable tags from skill name and detected tech stack (GAP 8)."""
        tags: List[str] = []

        # Parts of the skill name are always good tags
        tags.extend(p for p in skill_name.split("-") if len(p) > 2)

        # Add detected tech stack entries (deduplicated)
        for tech in tech_stack:
            if tech.lower() not in tags:
                tags.append(tech.lower())

        return list(dict.fromkeys(tags))[:6]  # deduplicate, cap at 6

    def _render_frontmatter(self, metadata: "SkillMetadata") -> str:
        """Emit Anthropic-spec-compliant YAML frontmatter (GAP 1 + GAP 4 + GAP 5).

        Spec requirements:
          - name: kebab-case, matches folder name
          - description: "[What it does]. Use when user mentions [triggers]."
          - license: MIT
          - allowed-tools: space-separated Claude tool names
          - metadata.author / version / category / tags
        """
        # GAP 4: embed trigger phrases directly in description text
        trigger_str = ", ".join(f'"{t}"' for t in metadata.auto_triggers[:5])
        base_desc = metadata.description.rstrip(".")
        desc = f"{base_desc}. Use when user mentions {trigger_str}."
        # GAP 5: append negative triggers to description
        if metadata.negative_triggers:
            neg_str = ", ".join(f'"{t}"' for t in metadata.negative_triggers[:3])
            desc += f" Do NOT activate for {neg_str}."
        desc = desc[:1024]

        # GAP 1: allowed-tools uses Claude's tool names, not CLI tools
        claude_tools = "Bash Read Write Edit Glob Grep"

        # GAP 8: tags derived from skill name + tech stack
        tags = metadata.tags if metadata.tags else [metadata.category]
        tags_str = "[" + ", ".join(tags) + "]"

        lines = [
            "---",
            f"name: {metadata.name}",
            "description: |",
            f"  {desc}",
            "license: MIT",
            f'allowed-tools: "{claude_tools}"',
            "metadata:",
            "  author: PRG",
            "  version: 1.0.0",
            f"  category: {metadata.category}",
            f"  tags: {tags_str}",
            "---",
            "",
        ]
        return "\n".join(lines)

    # Max total chars for supplementary docs (to stay within token budget)
    SUPPLEMENTARY_BUDGET = 1500

    # Filenames that are noise — never useful as skill context
    _DOCS_SKIP = {
        "readme.md",
        "changelog.md",
        "changelog",
        "license.md",
        "license",
        "contributing.md",
        "contributors.md",
        "authors.md",
        "history.md",
        "news.md",
        "releases.md",
        "security.md",
        "code_of_conduct.md",
    }

    # Filename signals that indicate high-value context docs (any project)
    _DOCS_HIGH_VALUE = {
        "spec",
        "architecture",
        "design",
        "constitution",
        "features",
        "preferences",
        "coding",
        "style",
        "guide",
        "workflow",
        "overview",
        "plan",
        "roadmap",
        "rules",
        "standards",
        "conventions",
        "adr",
    }

    def _score_doc(self, path: Path, content: str) -> int:
        """Score a supplementary doc by relevance. Higher = more useful."""
        stem = path.stem.lower()
        score = 0
        # High-value keyword in filename
        if any(kw in stem for kw in self._DOCS_HIGH_VALUE):
            score += 2
        # Bonus for being in a docs/ subdirectory (intentional documentation)
        if path.parent.name.lower() in ("docs", "doc", "documentation"):
            score += 1
        # Penalise very short files (likely stubs)
        if len(content) < 200:
            score -= 1
        return score

    def _discover_supplementary_docs(self) -> List[Path]:
        """Dynamically discover relevant .md docs in the project.

        Scans root + docs/ subdirectory, skips noise files (CHANGELOG, LICENSE …),
        and returns paths sorted by relevance score descending.
        Works for any project — no hardcoded filenames.
        """
        candidates: List[Path] = []

        search_dirs = [self.project_path] + [
            d for d in self.project_path.iterdir() if d.is_dir() and d.name.lower() in ("docs", "doc", "documentation")
        ]

        for directory in search_dirs:
            for md_file in directory.glob("*.md"):
                if md_file.name.lower() in self._DOCS_SKIP:
                    continue
                if md_file.name.lower() == "readme.md":
                    continue
                candidates.append(md_file)

        # Sort by score descending, then alphabetically for determinism
        candidates.sort(key=lambda p: (-self._score_doc(p, ""), p.name))
        return candidates

    def _load_key_files(self, skill_name: str) -> Dict[str, str]:
        """Load actual key project files to ground the LLM in real project content.

        Always includes: entry points + config + project tree +
        top supplementary docs discovered dynamically (no hardcoded names).
        Supplementary docs are capped at SUPPLEMENTARY_BUDGET total chars.
        """
        key_files: Dict[str, str] = {}
        skill_lower = skill_name.lower()

        # Always try to include entry points and config
        candidates = ["main.py", "app.py", "pyproject.toml", "requirements.txt"]

        # Topic-specific code file additions
        if any(w in skill_lower for w in ["backend", "api", "developer"]):
            candidates += ["project_rules_generator.py", "generator/__init__.py"]
        if "test" in skill_lower:
            candidates += ["pytest.ini", "tests/conftest.py"]
        if "cli" in skill_lower or "command" in skill_lower:
            candidates += ["main.py"]

        for candidate in candidates:
            path = self.project_path / candidate
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    key_files[candidate] = content[:600]
                except Exception:
                    pass

        # Project tree: always include (gives LLM structural grounding)
        tree = self._scan_project_tree()
        key_files["project_tree"] = tree[:800]

        # Supplementary docs: discovered dynamically, capped by total budget
        remaining_budget = self.SUPPLEMENTARY_BUDGET
        for doc_path in self._discover_supplementary_docs():
            if remaining_budget <= 0:
                break
            try:
                content = doc_path.read_text(encoding="utf-8", errors="ignore").strip()
                if not content:
                    continue
                # Re-score with actual content (short files get penalised)
                if self._score_doc(doc_path, content) < 0:
                    continue
                rel = str(doc_path.relative_to(self.project_path))
                chunk = content[:remaining_budget]
                key_files[rel] = chunk
                remaining_budget -= len(chunk)
            except Exception:
                pass

        return key_files

    def _generate_content(
        self,
        skill_name: str,
        readme_content: str,
        metadata: SkillMetadata,
        custom_context: Optional[Dict] = None,
        use_ai: bool = False,
        provider: str = "gemini",
    ) -> str:
        """Generate complete skill content using AI or templates."""

        # 1. AI Generation (if requested)
        if use_ai:
            try:
                from generator.llm_skill_generator import LLMSkillGenerator

                generator = LLMSkillGenerator(provider=provider)

                # Categorize tech stack for richer LLM context
                tech_list = self._detect_tech_stack(readme_content)
                _backend = {"fastapi", "flask", "django", "python", "express", "node", "fastapi"}
                _frontend = {"react", "vue", "angular", "typescript", "javascript", "nextjs"}
                _database = {"postgresql", "mysql", "mongodb", "redis", "sqlalchemy", "sqlite"}

                signals = set(metadata.project_signals)
                context = {
                    "readme": readme_content,
                    "tech_stack": {
                        "backend": [t for t in tech_list if t.lower() in _backend],
                        "frontend": [t for t in tech_list if t.lower() in _frontend],
                        "database": [t for t in tech_list if t.lower() in _database],
                        "languages": tech_list,
                    },
                    "structure": {
                        "has_docker": "has_docker" in signals,
                        "has_tests": "has_tests" in signals,
                        "has_api": "has_api" in signals,
                        "has_frontend": "has_frontend" in signals,
                        "has_database": "has_database" in signals,
                    },
                    # Load actual key project files for grounded generation
                    "key_files": self._load_key_files(skill_name),
                    "project_analysis": custom_context.get("project_analysis", {}) if custom_context else {},
                }

                print(f"🤖 Generating with AI ({provider})...")
                return generator.generate_skill(skill_name, context)
            except Exception as e:
                print(f"⚠️  AI generation failed: {e}. Falling back to templates.")

        # 2. Try Jinja2 template first, fallback to inline generation
        if HAS_JINJA2:
            try:
                return self._generate_with_jinja2(skill_name, readme_content, metadata, custom_context)
            except Exception as e:
                print(f"Warning: Jinja2 template failed ({e}), using inline generation")

        # Fallback: inline generation
        return self._generate_inline(skill_name, readme_content, metadata)

    def _generate_with_jinja2(
        self,
        skill_name: str,
        readme_content: str,
        metadata: SkillMetadata,
        custom_context: Optional[Dict] = None,
    ) -> str:
        """Generate using Jinja2 template."""
        template_dir = Path(__file__).parent.parent / "templates"
        template_path = template_dir / "SKILL.md.jinja2"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("SKILL.md.jinja2")

        # GAP 1/4/5: pre-compute spec-compliant description for the template
        trigger_str = ", ".join(f'"{t}"' for t in metadata.auto_triggers[:5])
        base_desc = metadata.description.rstrip(".")
        desc_with_triggers = f"{base_desc}. Use when user mentions {trigger_str}."
        if metadata.negative_triggers:
            neg_str = ", ".join(f'"{t}"' for t in metadata.negative_triggers[:3])
            desc_with_triggers += f" Do NOT activate for {neg_str}."
        desc_with_triggers = desc_with_triggers[:1024]

        tags = metadata.tags if metadata.tags else [metadata.category]

        # Build template context
        context = {
            "name": skill_name,
            "title": skill_name.replace("-", " ").title(),
            "description": metadata.description,
            "desc_with_triggers": desc_with_triggers,  # GAP 1/4/5
            "negative_triggers": metadata.negative_triggers,  # GAP 5
            "tags": tags,  # GAP 8
            "purpose": metadata.description,
            "purpose_extended": f"This skill provides step-by-step guidance for {skill_name.replace('-', ' ')}.",
            "auto_triggers": metadata.auto_triggers,
            "project_signals": metadata.project_signals,
            "tools": metadata.tools,
            "category": metadata.category,
            "priority": metadata.priority,
            "project_name": self.project_path.name,
            "project_path": str(self.project_path),
            "tech_stack": self._detect_tech_stack(readme_content),
            "readme_context": readme_content[:500] if readme_content else None,
            # BUG-C fix: quality_score removed — it is computed by _validate_quality()
            # *after* content generation. Hardcoding 95 here was misleading.
        }

        # Merge custom context
        if custom_context:
            context.update(custom_context)

        return template.render(**context)

    def _generate_inline(
        self,
        skill_name: str,
        readme_content: str,
        metadata: SkillMetadata,
    ) -> str:
        """Fallback inline generation (no Jinja2)."""
        title = skill_name.replace("-", " ").title()

        # Build content sections — frontmatter now follows Anthropic spec (GAP 1)
        content = self._render_frontmatter(metadata)
        content += f"""# Skill: {title}

## Purpose

{metadata.description}

This skill provides step-by-step guidance for {skill_name.replace("-", " ")}.

## Auto-Trigger

The agent should activate this skill when:

{self._format_triggers(metadata.auto_triggers)}

**Project Signals:**
{self._format_signals(metadata.project_signals)}

## Process

### 1. Analyze Current State

- Check project structure in `{self.project_path.name}/`
- Review relevant configuration files
- Identify existing patterns

### 2. Execute Core Steps

**Tools Required:** {", ".join(f"`{t}`" for t in metadata.tools)}

```bash
# Example workflow
cd {self.project_path.name}
# Run appropriate commands based on skill context
```

### 3. Validate Results

- Verify expected outputs
- Run tests if applicable
- Check for common issues

## Output

This skill generates:

- Modified/created files in project
- Status report of changes
- Recommendations for next steps

## Anti-Patterns

❌ **Don't** use generic commands without project context
✅ **Do** use actual project paths and configurations

❌ **Don't** skip validation steps
✅ **Do** always verify changes work as expected

## Tech Stack Notes

**Detected Technologies:** {", ".join(self._detect_tech_stack(readme_content))}

**Compatible Tools:** {", ".join(metadata.tools)}

## Project Context

```
Project: {self.project_path.name}
Signals: {", ".join(metadata.project_signals)}
```

---
*Generated by Cowork-Powered PRG Skill Creator*
"""

        return content

    def _format_triggers(self, triggers: List[str]) -> str:
        """Format triggers as markdown list."""
        return "\n".join(f"- {t}" for t in triggers)

    def _format_signals(self, signals: List[str]) -> str:
        """Format project signals as markdown list."""
        if not signals:
            return "- None detected"
        return "\n".join(f"- `{s}`" for s in signals)

    def _validate_quality(self, content: str, metadata: SkillMetadata) -> QualityReport:
        """
        Cowork's quality gates: ensure skill is actionable and specific.

        Delegates shared checks to quality_checker.validate_quality(), then adds
        the project-specific hallucination check that requires self.project_path.
        """
        from generator.utils.quality_checker import validate_quality

        report = validate_quality(content, metadata.auto_triggers, metadata.tools)

        # Project-specific: detect hallucinated file paths (needs self.project_path)
        hallucinated = self._detect_hallucinated_paths(content)
        if hallucinated:
            extra_issue = f"Hallucinated file paths: {', '.join(hallucinated[:3])}"
            score = max(0.0, report.score - 20)
            issues = report.issues + [extra_issue]
            return QualityReport(
                score=score,
                passed=score >= 70 and not issues,
                issues=issues,
                warnings=report.warnings,
                suggestions=report.suggestions,
            )

        return report

    def _detect_hallucinated_paths(self, content: str) -> List[str]:
        """
        Detect file paths that don't exist in project.

        This is critical for Cowork quality: no fake files!
        """
        hallucinated = []

        # Extract file path patterns
        patterns = [
            r"(?:File:|Path:|`)([\w/.-]+\.[\w]+)",  # File: path/to/file.py
            r"`(src/[\w/]+\.py)`",  # `src/module.py`
            r"(?:in|check|see) `([\w/.-]+\.[\w]+)`",  # in `file.py`
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                file_path = self.project_path / match
                if not file_path.exists():
                    hallucinated.append(match)

        return hallucinated

    def _auto_fix_quality_issues(self, content: str, quality: QualityReport) -> str:
        """Attempt to auto-fix common quality issues."""

        # Fix generic paths
        content = content.replace("cd project_name", f"cd {self.project_path.name}")
        content = content.replace("/path/to/project", str(self.project_path))

        # Remove placeholder sections if empty
        content = re.sub(r"\[describe.*?\]", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\[example.*?\]", "", content, flags=re.IGNORECASE)

        # Add anti-patterns if missing
        if "## Anti-Patterns" not in content:
            anti_pattern_section = """

## Anti-Patterns

❌ **Don't** use generic solutions without understanding project context
✅ **Do** analyze project structure first

❌ **Don't** skip validation steps
✅ **Do** always verify changes work
"""
            content += anti_pattern_section

        return content

    def export_to_file(
        self,
        content: str,
        metadata: SkillMetadata,
        output_dir: Path,
    ) -> Path:
        """Export skill to file in project .clinerules structure."""

        output_dir.mkdir(parents=True, exist_ok=True)
        skill_file = output_dir / f"{metadata.name}.md"

        skill_file.write_text(content, encoding="utf-8")

        return skill_file

    def auto_generate_skills(
        self,
        readme_content: str,
        output_dir: Path,
        quality_threshold: int = 70,
        auto_fix: bool = True,
    ) -> List[Path]:
        """
        Auto-generate skills based on detected tech stack.
        Returns list of generated file paths.
        """
        # Detect tech stack
        tech_stack = self._detect_tech_stack(readme_content)
        skill_names = []

        if not tech_stack:
            skill_names.append(f"{self.project_path.name}-workflow")
        else:
            # Map to skill types
            for tech in tech_stack:
                tech_lower = tech.lower()
                if tech_lower in ["fastapi", "flask", "django"]:
                    skill_names.append(f"{tech_lower}-api-workflow")
                elif tech_lower in ["react", "vue", "nextjs"]:
                    skill_names.append(f"{tech_lower}-component-builder")
                elif tech_lower == "pytest":
                    skill_names.append("pytest-testing-workflow")
                elif tech_lower == "docker":
                    skill_names.append("docker-deployment")
                elif tech_lower == "git":
                    skill_names.append("git-workflow")

            # Use detected skills + generic project workflow
            if not skill_names:
                skill_names.append(f"{self.project_path.name}-workflow")

        generated_files = []
        for skill_name in set(skill_names):  # Deduplicate
            try:
                content, metadata, quality = self.create_skill(skill_name, readme_content)

                if quality.score >= quality_threshold or auto_fix:
                    # Attempt auto-fix implies we use the potentially fixed content returned by create_skill
                    # (create_skill already calls _auto_fix_quality_issues if needed)
                    path = self.export_to_file(content, metadata, output_dir)
                    generated_files.append(path)
            except Exception as e:
                print(f"Warning: Failed to generate {skill_name}: {e}")

        return generated_files

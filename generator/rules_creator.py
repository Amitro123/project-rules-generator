"""
Cowork-Powered Rules Creator
============================

This module implements Cowork's intelligent rules creation logic for PRG.
It generates high-quality, project-specific rules with:
- Priority scoring (High/Medium/Low)
- Tech-specific patterns
- Anti-pattern extraction from git history
- Quality validation
- Conflict detection
"""

import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml


@dataclass
class Rule:
    """Single coding rule with priority."""

    content: str
    priority: str = "Medium"  # High, Medium, Low
    category: str = "General"  # Coding Standards, Architecture, Testing, etc.
    source: str = "analysis"  # analysis, git_history, tech_stack


@dataclass
class RulesMetadata:
    """Structured metadata for rules generation."""

    project_name: str
    tech_stack: List[str] = field(default_factory=list)
    project_type: str = "unknown"
    priority_areas: List[str] = field(default_factory=list)  # async_patterns, rest_api, etc.
    detected_signals: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Quality assessment of generated rules."""

    score: float  # 0-100
    passed: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    completeness: float = 0.0  # % of expected sections present
    conflicts: List[str] = field(default_factory=list)  # Contradictory rules


class CoworkRulesCreator:
    """
    Generates Cowork-quality rules for PRG projects.

    This creator combines:
    - Tech-specific rules (FastAPI -> REST patterns)
    - Priority scoring (High/Medium/Low)
    - Git history analysis for anti-patterns
    - Quality validation with conflict detection
    """

    # Technology-Specific Rules mapping (Cowork intelligence)
    TECH_RULES = {
        "fastapi": {
            "high": [
                "Use async/await for I/O operations (database, external APIs)",
                "Define Pydantic models for all request/response bodies",
                "Use Depends() for dependency injection (don't pass dependencies manually)",
                "Add response_model to all endpoints for validation",
            ],
            "medium": [
                "Use APIRouter for modular route organization",
                "Add OpenAPI tags and descriptions to endpoints",
                "Implement proper exception handlers with HTTPException",
                "Use BackgroundTasks for non-blocking operations",
            ],
            "low": [
                "Add request/response examples in docstrings",
                "Use status codes from fastapi.status module",
            ],
        },
        "react": {
            "high": [
                "Use functional components with hooks (not class components)",
                "Keep components pure - avoid side effects in render",
                "Use useCallback/useMemo for expensive computations",
                "Avoid prop drilling - use Context or state management",
            ],
            "medium": [
                "Split large components into smaller, reusable ones",
                "Use custom hooks to extract reusable logic",
                "Implement error boundaries for graceful failures",
                "Use React.lazy() for code splitting",
            ],
            "low": [
                "Add PropTypes or TypeScript for type safety",
                "Use React DevTools for debugging",
            ],
        },
        "pytest": {
            "high": [
                "Use fixtures for test setup/teardown (don't repeat setup)",
                "Parametrize tests with @pytest.mark.parametrize",
                "Mock external dependencies (APIs, databases)",
            ],
            "medium": [
                "Organize tests in tests/ mirroring source structure",
                "Use conftest.py for shared fixtures",
                "Add docstrings explaining what each test validates",
            ],
            "low": [
                "Use pytest.raises() for exception testing",
                "Add markers (@pytest.mark.slow) for test categories",
            ],
        },
        "docker": {
            "high": [
                "Use multi-stage builds to minimize image size",
                "Don't run containers as root (use USER directive)",
                "Pin specific versions in base images (not :latest)",
            ],
            "medium": [
                "Use .dockerignore to exclude unnecessary files",
                "Set health checks with HEALTHCHECK directive",
                "Use docker-compose for multi-container setups",
            ],
        },
        "asyncio": {
            "high": [
                "Always use async/await (not callbacks or futures)",
                "Don't mix blocking and async code in same function",
                "Use asyncio.gather() for concurrent operations",
            ],
            "medium": [
                "Implement proper exception handling in async tasks",
                "Use asyncio.create_task() for fire-and-forget operations",
                "Add timeouts to async operations (asyncio.wait_for)",
            ],
        },
        "sqlalchemy": {
            "high": [
                "Use async SQLAlchemy for async frameworks",
                "Always use sessions properly (with context manager)",
                "Define relationships with lazy='selectin' to avoid N+1",
            ],
            "medium": [
                "Use Alembic for database migrations",
                "Add indexes on frequently queried columns",
                "Implement soft deletes for critical data",
            ],
        },
        "click": {
            "high": [
                "Keep @click.command() functions thin — delegate logic to generator/ modules",
                "Use click.testing.CliRunner for all CLI integration tests",
                "Always set exit codes explicitly: sys.exit(0) success, sys.exit(1) failure",
                "Use click.echo() for output, never print() directly in command functions",
            ],
            "medium": [
                "Group related commands with @click.group() and register in cli.py",
                "Add --verbose / -v flag to every command for debug output",
                "Use click.Path(exists=True) for path arguments to validate early",
                "Add help strings to every @click.option() and @click.argument()",
            ],
            "low": [
                "Use click.confirm() for destructive operations",
                "Add epilog= to commands showing usage examples",
            ],
        },
        "pydantic": {
            "high": [
                "Define Pydantic models for all structured data (not raw dicts)",
                "Use Field() with description= for self-documenting models",
                "Validate at the boundary — parse input into models as early as possible",
            ],
            "medium": [
                "Use model_validator for cross-field validation logic",
                "Prefer model.model_dump() over dict() (Pydantic v2)",
                "Use Optional[X] = None for truly optional fields, not X = None",
            ],
            "low": [
                "Add json_schema_extra for OpenAPI documentation hints",
            ],
        },
        "jinja2": {
            "high": [
                "Store all templates in templates/ with .jinja2 extension",
                "Never build markdown/HTML by string concatenation — use templates",
                "Use Environment(autoescape=False) for markdown templates (not HTML)",
            ],
            "medium": [
                "Pass only the data the template needs — avoid passing full objects",
                "Use {%- and -%} to control whitespace in generated output",
                "Test template rendering in unit tests with known fixture data",
            ],
        },
        "groq": {
            "high": [
                "Always use the GroqClient wrapper — never call the Groq API directly",
                "Set GROQ_API_KEY via environment variable, never hardcode",
                "Handle groq.RateLimitError with exponential backoff retry",
            ],
            "medium": [
                "Use llama-3.1-8b-instant for fast tasks, llama-3.3-70b for quality",
                "Log token usage per request for cost monitoring",
                "Implement provider fallback: Groq -> Gemini on failure",
            ],
        },
        "gemini": {
            "high": [
                "Always use the GeminiClient wrapper — never call the Gemini API directly",
                "Set GEMINI_API_KEY via environment variable, never hardcode",
                "Handle google.api_core.exceptions.ResourceExhausted with retry",
            ],
            "medium": [
                "Use gemini-2.0-flash for speed, gemini-1.5-pro for complex reasoning",
                "Implement provider fallback: Gemini -> Groq on quota exhaustion",
                "Log model name and token count for every API call",
            ],
        },
    }

    # Anti-patterns to detect from git history
    GIT_ANTIPATTERNS = {
        "repeated_fixes": "Frequent fixes to same file",
        "large_commits": "Commits with 500+ lines",
        "merge_conflicts": "Frequent merge conflicts",
        "reverted_commits": "Commits that were reverted",
    }

    def __init__(self, project_path: Path, provider: str = "groq"):
        """Initialize with project path for context awareness."""
        self.project_path = project_path
        self.provider = provider
        self._git_available = self._check_git_available()

    def create_rules(
        self,
        readme_content: str,
        tech_stack: Optional[List[str]] = None,
        enhanced_context: Optional[Dict] = None,
    ) -> Tuple[str, RulesMetadata, QualityReport]:
        """
        Create Cowork-quality rules with full intelligence.

        Args:
            readme_content: Project README content
            tech_stack: Technologies used (auto-detected if None)
            enhanced_context: Additional context from project analyzer

        Returns:
            Tuple of (rules_content, metadata, quality_report)
        """
        # 1. Build metadata
        metadata = self._build_metadata(readme_content, tech_stack, enhanced_context)

        # 2. Generate rules by category
        rules_by_category = self._generate_rules(metadata, enhanced_context)

        # 3. Extract anti-patterns from git history
        if self._git_available:
            git_antipatterns = self._extract_git_antipatterns()
            if git_antipatterns:
                rules_by_category["Anti-Patterns from History"] = git_antipatterns

        # 4. Generate content
        content = self._generate_content(metadata, rules_by_category, readme_content)

        # 5. Quality validation
        quality = self._validate_quality(content, metadata, rules_by_category)

        return content, metadata, quality

    def _build_metadata(
        self,
        readme_content: str,
        tech_stack: Optional[List[str]],
        enhanced_context: Optional[Dict],
    ) -> RulesMetadata:
        """Build smart metadata with Cowork intelligence."""

        # Extract project name
        project_name = self.project_path.name

        # Detect tech stack
        if tech_stack is None:
            tech_stack = self._detect_tech_stack(readme_content, enhanced_context)

        # Detect project type
        project_type = self._detect_project_type(tech_stack, enhanced_context)

        # Identify priority areas
        priority_areas = self._identify_priority_areas(tech_stack, project_type)

        # Detect project signals
        signals = self._detect_signals()

        return RulesMetadata(
            project_name=project_name,
            tech_stack=tech_stack,
            project_type=project_type,
            priority_areas=priority_areas,
            detected_signals=signals,
        )

    def _detect_tech_stack(self, readme_content: str, enhanced_context: Optional[Dict]) -> List[str]:
        """Auto-detect tech stack from README, project files, and context."""
        tech_keywords = {
            # Web frameworks
            "fastapi",
            "flask",
            "django",
            "express",
            # Frontend
            "react",
            "vue",
            "angular",
            # Testing
            "pytest",
            "jest",
            "vitest",
            # DevOps
            "docker",
            "kubernetes",
            # Async
            "asyncio",
            "celery",
            # Databases
            "sqlalchemy",
            "prisma",
            "mongoose",
            # Languages
            "typescript",
            "python",
            "node",
            "go",
            "rust",
            # Databases
            "postgresql",
            "mongodb",
            "redis",
            # AI/LLM
            "openai",
            "anthropic",
            "langchain",
            "groq",
            "gemini",
            # CLI / validation / templates
            "click",
            "typer",
            "argparse",
            "pydantic",
            "jinja2",
        }

        detected: Set[str] = set()

        # Scan project files first (authoritative)
        self._detect_from_files(detected)
        file_detected = set(detected)  # snapshot of what files confirmed

        # From README — only add if confirmed by files OR it's a core language keyword
        # This prevents false positives from docs/examples mentioning other tech stacks
        core_language_keywords = {"python", "typescript", "node", "go", "rust"}
        readme_lower = readme_content.lower()
        for tech in tech_keywords:
            if tech in readme_lower:
                if tech in file_detected or tech in core_language_keywords:
                    detected.add(tech)

        # From enhanced context (always trusted)
        if enhanced_context:
            context_tech = enhanced_context.get("project_data", {}).get("tech_stack", [])
            detected.update(t.lower() for t in context_tech)

        return list(sorted(detected))

    def _detect_from_files(self, detected: Set[str]) -> None:
        """Scan project files to detect tech stack signals."""
        # Check requirements.txt / pyproject.toml / setup.py
        req_files = [
            self.project_path / "requirements.txt",
            self.project_path / "requirements-dev.txt",
            self.project_path / "pyproject.toml",
            self.project_path / "setup.py",
            self.project_path / "setup.cfg",
        ]
        file_tech_map = {
            "pytest": ["pytest"],
            "click": ["click"],
            "pydantic": ["pydantic"],
            "jinja2": ["jinja2", "jinja"],
            "fastapi": ["fastapi"],
            "groq": ["groq"],
            "gemini": ["google-generativeai", "google-genai", "gemini"],
            "sqlalchemy": ["sqlalchemy"],
            "docker": ["docker"],
        }
        for req_file in req_files:
            if req_file.exists():
                try:
                    content = req_file.read_text(encoding="utf-8", errors="ignore").lower()
                    for tech, keywords in file_tech_map.items():
                        if any(kw in content for kw in keywords):
                            detected.add(tech)
                except Exception:
                    pass

        # Check for pytest.ini / conftest.py -> pytest
        if any((self.project_path / f).exists() for f in ["pytest.ini", "conftest.py", "pyproject.toml"]):
            if (self.project_path / "tests").exists() or (self.project_path / "test").exists():
                detected.add("pytest")

        # Check for Jinja2 templates directory
        if (self.project_path / "templates").exists():
            detected.add("jinja2")

    def _detect_project_type(self, tech_stack: List[str], enhanced_context: Optional[Dict]) -> str:
        """Detect project type (python-cli, fastapi-api, react-app, etc.)."""

        # Inference from tech stack (authoritative — checked first)
        if "fastapi" in tech_stack or "flask" in tech_stack:
            return "python-api"
        elif "react" in tech_stack or "vue" in tech_stack:
            return "frontend-app"
        elif "langchain" in tech_stack or "openai" in tech_stack:
            return "ai-agent"
        elif "click" in tech_stack or "typer" in tech_stack or "argparse" in tech_stack:
            return "python-cli"
        elif "pytest" in tech_stack:
            return "python-library"
        elif "docker" in tech_stack:
            return "containerized-app"

        # Fall back to enhanced_context only when tech stack gives no signal
        if enhanced_context:
            proj_type = enhanced_context.get("metadata", {}).get("project_type", "")
            if proj_type and proj_type not in ("unknown", ""):
                return proj_type

        return "python-library"

    def _identify_priority_areas(self, tech_stack: List[str], project_type: str) -> List[str]:
        """Identify high-priority areas for this project."""
        priorities = []

        # From tech stack
        if "fastapi" in tech_stack or "flask" in tech_stack:
            priorities.append("rest_api_patterns")
            priorities.append("async_operations")

        if "react" in tech_stack:
            priorities.append("hooks_patterns")
            priorities.append("state_management")

        if "asyncio" in tech_stack or "fastapi" in tech_stack:
            priorities.append("async_coordination")

        if "docker" in tech_stack:
            priorities.append("containerization")

        if "pytest" in tech_stack or "jest" in tech_stack:
            priorities.append("test_coverage")

        if "openai" in tech_stack or "anthropic" in tech_stack:
            priorities.append("llm_integration")

        # AI/LLM providers (broader coverage)
        if any(t in tech_stack for t in ("gemini", "groq", "claude", "langchain", "llm")):
            priorities.append("llm_integration")

        # CLI tools
        if any(t in tech_stack for t in ("click", "typer", "argparse")):
            priorities.append("cli_ux_patterns")

        # Data validation
        if any(t in tech_stack for t in ("pydantic", "marshmallow")):
            priorities.append("data_validation")

        # Project type fallbacks
        if project_type == "python-cli" and not priorities:
            priorities.extend(["cli_ux_patterns", "error_handling"])
        elif project_type == "python-library" and not priorities:
            priorities.extend(["test_coverage", "api_design"])

        return list(dict.fromkeys(priorities))  # deduplicate, preserve order

    def _detect_signals(self) -> List[str]:
        """Detect project structure signals."""
        signals = []

        checks = {
            "has_docker": ["Dockerfile", "docker-compose.yml"],
            "has_tests": ["tests/", "test/", "pytest.ini"],
            "has_ci": [".github/workflows/", ".gitlab-ci.yml"],
            "has_api": ["api/", "routes/", "app.py"],
            "has_frontend": ["frontend/", "src/components/"],
            "has_database": ["migrations/", "alembic/", "models.py"],
        }

        for signal, indicators in checks.items():
            for indicator in indicators:
                if (self.project_path / indicator).exists():
                    signals.append(signal)
                    break

        return signals

    def _generate_rules_via_llm(
        self,
        metadata: RulesMetadata,
        readme_content: str = "",
    ) -> Dict[str, List[Rule]]:
        """Generate rules via LLM when tech stack is unknown or unrecognized.

        Called as fallback when no tech in metadata.tech_stack exists in TECH_RULES.
        Parses the LLM response into Rule objects. Falls back to generic rules on failure.
        """
        from generator.utils.readme_bridge import build_project_tree

        tree = build_project_tree(self.project_path)

        # Load a few key files for grounding (lightweight version)
        snippets: list[str] = []
        for fname in [
            "main.py",
            "app.py",
            "pyproject.toml",
            "requirements.txt",
            "package.json",
            "Cargo.toml",
            "go.mod",
        ]:
            p = self.project_path / fname
            if p.exists():
                try:
                    snippets.append(f"[{fname}]\n{p.read_text(encoding='utf-8', errors='ignore')[:400]}")
                except Exception:
                    pass

        prompt = f"""You are generating coding rules for a software project.

Project: {metadata.project_name}
Tech stack detected: {", ".join(metadata.tech_stack) or "unknown"}
Project tree:
{tree}

Key files:
{chr(10).join(snippets) or "No key files found."}

README excerpt:
{readme_content[:600] or "No README."}

Generate 6-10 specific, actionable coding rules for this project.
Format strictly as:
DO: <rule>
DO: <rule>
DONT: <rule>
DONT: <rule>

Rules must be specific to this tech stack and project structure.
No explanations, no markdown, just the DO:/DONT: lines."""

        try:
            from generator.llm_skill_generator import LLMSkillGenerator

            generator = LLMSkillGenerator(provider=self.provider)
            response = generator.generate_content(prompt, max_tokens=600)

            rules_by_category: Dict[str, List[Rule]] = defaultdict(list)
            for line in response.splitlines():
                line = line.strip()
                if line.upper().startswith("DO:"):
                    rules_by_category["Coding Standards"].append(
                        Rule(
                            content=line[3:].strip(),
                            priority="High",
                            category="Coding Standards",
                            source="llm_fallback",
                        )
                    )
                elif line.upper().startswith("DONT:") or line.upper().startswith("DON'T:"):
                    content = line.split(":", 1)[-1].strip()
                    rules_by_category["Coding Standards"].append(
                        Rule(
                            content=f"Don't {content}",
                            priority="High",
                            category="Coding Standards",
                            source="llm_fallback",
                        )
                    )

            if rules_by_category:
                print(
                    f"✨ LLM generated {sum(len(v) for v in rules_by_category.values())} rules for unknown tech stack."
                )
                return dict(rules_by_category)

        except Exception as e:
            print(f"⚠️  LLM rules fallback failed ({e}). Using generic rules.")

        # Final fallback — return empty so _generate_rules continues to generic
        return {}

    def _generate_rules(
        self,
        metadata: RulesMetadata,
        enhanced_context: Optional[Dict],
    ) -> Dict[str, List[Rule]]:
        """Generate rules organized by category with priorities."""

        rules_by_category = defaultdict(list)

        # Detect whether any tech is actually recognized in TECH_RULES.
        # If none are, fall back to LLM rather than producing empty output silently.
        recognized = [t for t in metadata.tech_stack if t.lower() in self.TECH_RULES]
        if metadata.tech_stack and not recognized:
            llm_rules = self._generate_rules_via_llm(metadata)
            if llm_rules:
                # Still append generic rules and return
                generic_rules = self._generate_generic_rules(metadata)
                llm_rules.setdefault("General", []).extend(generic_rules)
                return llm_rules

        # 1. Tech-specific rules (Cowork intelligence!)
        for tech in metadata.tech_stack:
            tech_lower = tech.lower()
            if tech_lower in self.TECH_RULES:
                tech_rules = self.TECH_RULES[tech_lower]

                # Add high-priority rules
                for rule_content in tech_rules.get("high", []):
                    rules_by_category["Coding Standards"].append(
                        Rule(
                            content=rule_content,
                            priority="High",
                            category="Coding Standards",
                            source=f"{tech}_patterns",
                        )
                    )

                # Add medium-priority rules
                for rule_content in tech_rules.get("medium", []):
                    rules_by_category["Best Practices"].append(
                        Rule(
                            content=rule_content,
                            priority="Medium",
                            category="Best Practices",
                            source=f"{tech}_patterns",
                        )
                    )

                # Add low-priority rules
                for rule_content in tech_rules.get("low", []):
                    rules_by_category["Recommendations"].append(
                        Rule(
                            content=rule_content,
                            priority="Low",
                            category="Recommendations",
                            source=f"{tech}_patterns",
                        )
                    )

        # 2. Architecture rules from project type
        arch_rules = self._generate_architecture_rules(metadata)
        if arch_rules:
            rules_by_category["Architecture"].extend(arch_rules)

        # 3. Testing rules — populate if pytest in tech_stack OR has_tests signal
        has_test_signal = (
            "pytest" in metadata.tech_stack or "jest" in metadata.tech_stack or "has_tests" in metadata.detected_signals
        )
        if has_test_signal:
            test_rules = self._generate_testing_rules(metadata)
            rules_by_category["Testing"].extend(test_rules)

        # 4. Generic rules
        generic_rules = self._generate_generic_rules(metadata)
        rules_by_category["General"].extend(generic_rules)

        return dict(rules_by_category)

    def _generate_architecture_rules(self, metadata: RulesMetadata) -> List[Rule]:
        """Generate architecture-specific rules."""
        rules = []

        if metadata.project_type == "python-api":
            rules.append(
                Rule(
                    "Use layered architecture: routes -> services -> repositories",
                    priority="High",
                    category="Architecture",
                )
            )
            rules.append(
                Rule(
                    "Keep route handlers thin - move logic to service layer",
                    priority="High",
                    category="Architecture",
                )
            )

        if metadata.project_type == "python-cli":
            rules.append(
                Rule(
                    "CLI commands live in refactor/ — core logic lives in generator/",
                    priority="High",
                    category="Architecture",
                )
            )
            rules.append(
                Rule(
                    "Register all new commands in refactor/cli.py — never add to main.py",
                    priority="High",
                    category="Architecture",
                )
            )
            rules.append(
                Rule(
                    "Always use encoding='utf-8' when reading/writing files — never rely on system default",
                    priority="High",
                    category="Architecture",
                )
            )

        if metadata.project_type == "ai-agent":
            rules.append(
                Rule(
                    "Single orchestrator pattern - one main coordinator",
                    priority="High",
                    category="Architecture",
                )
            )
            rules.append(
                Rule(
                    "Implement error boundaries for LLM failures",
                    priority="High",
                    category="Architecture",
                )
            )

        if metadata.project_type == "frontend-app":
            rules.append(
                Rule(
                    "Component-based architecture - single responsibility",
                    priority="High",
                    category="Architecture",
                )
            )

        return rules

    def _generate_testing_rules(self, metadata: RulesMetadata) -> List[Rule]:
        """Generate testing-specific rules."""
        rules = []

        test_framework = None
        if "pytest" in metadata.tech_stack:
            test_framework = "pytest"
        elif "jest" in metadata.tech_stack:
            test_framework = "jest"

        if test_framework:
            rules.append(
                Rule(
                    f"Run {test_framework} before committing",
                    priority="High",
                    category="Testing",
                )
            )
            rules.append(
                Rule(
                    "Add tests for all new features",
                    priority="High",
                    category="Testing",
                )
            )
            rules.append(
                Rule(
                    "Maintain test coverage above 70%",
                    priority="Medium",
                    category="Testing",
                )
            )

        return rules

    def _generate_generic_rules(self, metadata: RulesMetadata) -> List[Rule]:
        """Generate generic best practices."""
        return [
            Rule(
                "Follow existing project structure and naming conventions",
                priority="High",
                category="General",
            ),
            Rule(
                "Add docstrings to all public functions/classes",
                priority="Medium",
                category="General",
            ),
            Rule(
                "Don't commit secrets, API keys, or .env files",
                priority="High",
                category="General",
            ),
        ]

    def _extract_git_antipatterns(self) -> List[Rule]:
        """Extract anti-patterns from git history (Cowork magic!)."""
        antipatterns = []

        try:
            # Check for frequently modified files (hot spots)
            result = subprocess.run(
                ["git", "log", "--pretty=format:", "--name-only", "--max-count=200"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )

            if result.returncode == 0:
                file_changes: Dict[str, int] = defaultdict(int)
                for line in result.stdout.split("\n"):
                    if line.strip():
                        file_changes[line] += 1

                # Find hot spots (files changed > 10 times)
                hotspots = [f for f, count in file_changes.items() if count > 10]

                if hotspots:
                    antipatterns.append(
                        Rule(
                            f"🔥 Hot spots detected: {', '.join(hotspots[:3])} - consider refactoring",
                            priority="Medium",
                            category="Anti-Patterns from History",
                            source="git_history",
                        )
                    )

            # Check for large commits (> 500 lines)
            result = subprocess.run(
                ["git", "log", "--shortstat", "--oneline", "-10"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )

            if result.returncode == 0:
                large_commits = 0
                for line in result.stdout.split("\n"):
                    match = re.search(r"(\d+) insertions?\(\+\)", line)
                    if match and int(match.group(1)) > 500:
                        large_commits += 1

                if large_commits > 2:
                    antipatterns.append(
                        Rule(
                            "🔥 Large commits detected - break down changes into smaller commits",
                            priority="Low",
                            category="Anti-Patterns from History",
                            source="git_history",
                        )
                    )

        except Exception:
            # Git analysis failed, skip
            pass

        return antipatterns

    def _generate_content(
        self,
        metadata: RulesMetadata,
        rules_by_category: Dict[str, List[Rule]],
        readme_content: str,
    ) -> str:
        """Generate complete rules.md content."""

        # YAML frontmatter
        frontmatter = {
            "project": metadata.project_name,
            "tech_stack": metadata.tech_stack,
            "priority_rules": metadata.priority_areas,
            "project_type": metadata.project_type,
            "version": "2.0",
            "generated": "cowork-powered",
        }

        yaml_str = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)

        # Build content
        content = f"""---
{yaml_str}---

# {metadata.project_name} - Coding Rules

**Generated by Cowork-Powered Rules Creator** 🤖

## 📋 Priority Areas

{self._format_priority_areas(metadata.priority_areas)}

## 💻 Coding Standards

"""

        # Collect all rules flat for priority view
        # Deduplicate rules by (category, content) before rendering
        seen_category_content: Set[tuple] = set()
        deduped: Dict[str, List[Rule]] = {}
        for cat, rules in rules_by_category.items():
            deduped[cat] = []
            for rule in rules:
                key = (rule.category, rule.content)
                if key not in seen_category_content:
                    seen_category_content.add(key)
                    deduped[cat].append(rule)
        rules_by_category = deduped

        all_rules_flat = [rule for rules in rules_by_category.values() for rule in rules]

        # Add rules by priority (Coding Standards section)
        shown_in_priority: Set[str] = set()
        for priority in ["High", "Medium", "Low"]:
            priority_rules = [r for r in all_rules_flat if r.priority == priority]
            if priority_rules:
                content += f"\n### {priority} Priority\n\n"
                for rule in priority_rules:
                    content += f"- ✅ **{rule.content}**\n"
                    shown_in_priority.add(rule.content)

        # Add rules by category — only rules NOT already shown in priority view
        # This eliminates the duplication between the two sections
        content += "\n## 📂 Rules by Category\n\n"

        priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
        for category, rules in sorted(rules_by_category.items()):
            # Only include rules unique to this category (not already in priority view)
            unique_rules = [r for r in rules if r.content not in shown_in_priority]
            if not unique_rules:
                continue
            content += f"\n### {category}\n\n"
            for rule in unique_rules:
                emoji = priority_emoji.get(rule.priority, "🟢")
                content += f"- {emoji} {rule.content}\n"

        # Add tech stack section
        content += "\n## 🛠️ Tech Stack\n\n"
        for tech in metadata.tech_stack:
            content += f"- {tech}\n"

        # Add project signals
        if metadata.detected_signals:
            content += "\n## 🏗️ Project Structure\n\n"
            for signal in metadata.detected_signals:
                content += f"- `{signal}`\n"

        content += "\n---\n"
        content += "*Generated by Cowork-Powered PRG Rules Creator*\n"
        content += f"*Tech Stack: {len(metadata.tech_stack)} | Rules: {sum(len(rules) for rules in rules_by_category.values())} | Quality: Cowork-level*\n"

        return content

    def _format_priority_areas(self, areas: List[str]) -> str:
        """Format priority areas as markdown list."""
        if not areas:
            return "- No specific priority areas detected"

        formatted = []
        for area in areas:
            readable = area.replace("_", " ").title()
            formatted.append(f"- **{readable}**")

        return "\n".join(formatted)

    def _validate_quality(
        self,
        content: str,
        metadata: RulesMetadata,
        rules_by_category: Dict[str, List[Rule]],
    ) -> QualityReport:
        """Validate rules quality with Cowork standards."""

        issues = []
        warnings = []
        score = 100.0

        # 1. Check completeness
        required_sections = [
            "Coding Standards",
            "Priority Areas",
            "Tech Stack",
        ]

        completeness = sum(1 for sec in required_sections if sec in content) / len(required_sections)

        if completeness < 1.0:
            issues.append(f"Missing sections (completeness: {completeness * 100:.0f}%)")
            score -= 20

        # 2. Check for sufficient rules
        total_rules = sum(len(rules) for rules in rules_by_category.values())
        if total_rules < 5:
            warnings.append(f"Only {total_rules} rules generated (recommend 10+)")
            score -= 10

        # 3. Check for priority distribution
        high_priority = sum(1 for rules in rules_by_category.values() for rule in rules if rule.priority == "High")

        if high_priority < 2:
            warnings.append("Few high-priority rules (recommend 3+)")
            score -= 5

        # 4. Detect rule conflicts
        conflicts = self._detect_rule_conflicts(rules_by_category)
        if conflicts:
            issues.extend(conflicts)
            score -= len(conflicts) * 10

        # 5. Check for tech-specific rules
        if not any(rule.source.endswith("_patterns") for rules in rules_by_category.values() for rule in rules):
            warnings.append("No tech-specific rules (may be too generic)")
            score -= 5

        passed = score >= 85 and len(issues) == 0

        return QualityReport(
            score=max(0, score),
            passed=passed,
            issues=issues,
            warnings=warnings,
            completeness=completeness,
            conflicts=conflicts,
        )

    def _detect_rule_conflicts(self, rules_by_category: Dict[str, List[Rule]]) -> List[str]:
        """Detect genuinely contradictory rules (same topic, opposite direction)."""
        conflicts = []

        all_rules = [rule.content.lower() for rules in rules_by_category.values() for rule in rules]

        # Check for explicit contradictions: "use X" vs "don't use X" about the same thing
        # We require both terms to appear in the same rule, not just anywhere in the ruleset
        conflict_pairs = [
            ("use async", "don't use async"),
            ("use class components", "don't use class components"),
            ("use sync", "don't use sync"),
        ]

        for positive, negative in conflict_pairs:
            has_positive = any(positive in rule for rule in all_rules)
            has_negative = any(negative in rule for rule in all_rules)

            if has_positive and has_negative:
                conflicts.append(f"Conflicting rules about '{positive}'")

        return conflicts

    def _check_git_available(self) -> bool:
        """Check if git is available and project is a git repo."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_path,
                capture_output=True,
                timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def export_to_file(
        self,
        content: str,
        metadata: RulesMetadata,
        output_dir: Path,
        filename: str = "rules.md",
    ) -> Path:
        """Export rules to file in .clinerules structure."""

        output_dir.mkdir(parents=True, exist_ok=True)
        rules_file = output_dir / filename

        rules_file.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))

        return rules_file

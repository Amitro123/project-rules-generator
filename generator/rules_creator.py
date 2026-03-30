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
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

from generator.base_generator import ArtifactGenerator
from generator.quality_validators import RulesQualityValidator
from generator.rules_git_miner import RulesGitMiner
from generator.rules_renderer import RulesContentRenderer, append_mandatory_anti_patterns  # noqa: F401 (re-export)
from generator.tech_registry import TECH_RULES as _TECH_RULES


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



class CoworkRulesCreator(ArtifactGenerator):
    """
    Generates Cowork-quality rules for PRG projects.

    Inherits from ArtifactGenerator to enforce strategic depth:
    every rule carries a WHY clause explaining what breaks without it.

    This creator combines:
    - Tech-specific rules (FastAPI -> REST patterns)
    - Priority scoring (High/Medium/Low)
    - Git history analysis for anti-patterns
    - Quality validation with conflict detection
    """

    # Technology-Specific Rules mapping (single source of truth: tech_registry.py)
    TECH_RULES = _TECH_RULES

    def __init__(self, project_path: Path, provider: str = "groq"):
        """Initialize with project path for context awareness."""
        self.project_path = project_path
        self.provider = provider
        self._git_miner = RulesGitMiner(project_path)
        self._git_available = self._git_miner.available
        self._quality_validator = RulesQualityValidator()
        self._renderer = RulesContentRenderer()

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
        git_antipatterns = self._git_miner.extract_antipatterns()
        if git_antipatterns:
            rules_by_category["Anti-Patterns from History"] = git_antipatterns

        # 4. Generate content
        content = self._renderer.render(metadata, rules_by_category, readme_content)

        # 5. Quality validation
        quality = self._quality_validator.validate(content, metadata, rules_by_category)

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
        """Auto-detect tech stack from README, project files, and optional enhanced context.

        Delegates file/README detection to generator.utils.tech_detector.detect_tech_stack().
        enhanced_context (from EnhancedProjectParser) is merged in as additional signal.
        """
        from generator.utils.tech_detector import detect_tech_stack as _detect_tech_stack_util

        detected: Set[str] = set(_detect_tech_stack_util(self.project_path, readme_content))

        # Enhanced context is always trusted (from EnhancedProjectParser)
        if enhanced_context:
            context_tech = enhanced_context.get("project_data", {}).get("tech_stack", [])
            detected.update(t.lower() for t in context_tech)

        return list(sorted(detected))

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

    def _build_prompt(self, metadata: "RulesMetadata", readme_content: str = "") -> str:
        """Build the LLM prompt for rules generation.

        Embeds _PAIN_FIRST_PREAMBLE and _WHY_RULE_FORMAT so every generated
        rule carries a WHY clause explaining what breaks without it.
        """
        from generator.utils.readme_bridge import build_project_tree

        tree = build_project_tree(self.project_path)

        snippets: List[str] = []
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
                except OSError:
                    pass

        return (
            f"{self._PAIN_FIRST_PREAMBLE}\n"
            f"{self._WHY_RULE_FORMAT}\n"
            f"Project: {metadata.project_name}\n"
            f"Tech stack detected: {', '.join(metadata.tech_stack) or 'unknown'}\n"
            f"Project tree:\n{tree}\n\n"
            f"Key files:\n{chr(10).join(snippets) or 'No key files found.'}\n\n"
            f"README excerpt:\n{readme_content[:600] or 'No README.'}\n\n"
            f"Generate 6-10 specific, actionable coding rules for this project.\n"
            f"Rules must be specific to this tech stack and project structure.\n"
            f"No extra markdown — only DO:/DONT: lines with | WHY: clauses."
        )

    def _generate_rules_via_llm(
        self,
        metadata: RulesMetadata,
        readme_content: str = "",
    ) -> Dict[str, List[Rule]]:
        """Generate rules via LLM when tech stack is unknown or unrecognized.

        Called as fallback when no tech in metadata.tech_stack exists in TECH_RULES.
        Parses the LLM response into Rule objects. Falls back to generic rules on failure.
        """
        prompt = self._build_prompt(metadata, readme_content)

        try:
            from generator.llm_skill_generator import LLMSkillGenerator

            generator = LLMSkillGenerator(provider=self.provider)
            response = generator.generate_content(prompt, max_tokens=600)

            rules_by_category: Dict[str, List[Rule]] = defaultdict(list)
            for line in response.splitlines():
                line = line.strip()
                if line.upper().startswith("DO:"):
                    raw = line[3:].strip()
                    if "|" in raw:
                        rule_part, why_part = raw.split("|", 1)
                        why_part = re.sub(r"(?i)^why:\s*", "", why_part.strip())
                        content = self.format_rule_with_why(rule_part.strip(), why_part)
                    else:
                        content = raw
                    rules_by_category["Coding Standards"].append(
                        Rule(
                            content=content,
                            priority="High",
                            category="Coding Standards",
                            source="llm_fallback",
                        )
                    )
                elif line.upper().startswith("DONT:") or line.upper().startswith("DON'T:"):
                    raw = line.split(":", 1)[-1].strip()
                    if "|" in raw:
                        rule_part, why_part = raw.split("|", 1)
                        why_part = re.sub(r"(?i)^why:\s*", "", why_part.strip())
                        content = self.format_rule_with_why(f"Don't {rule_part.strip()}", why_part)
                    else:
                        content = f"Don't {raw}"
                    rules_by_category["Coding Standards"].append(
                        Rule(
                            content=content,
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
                    "Keep @click.command() / @app.command() functions thin — delegate business logic to core modules",
                    priority="High",
                    category="Architecture",
                )
            )
            rules.append(
                Rule(
                    "Register all new CLI commands in a dedicated entry-point module — never add commands directly to main.py",
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
        """Delegate to RulesGitMiner."""
        return self._git_miner.extract_antipatterns()

    def _generate_content(
        self,
        metadata: RulesMetadata,
        rules_by_category: Dict[str, List[Rule]],
        readme_content: str,
    ) -> str:
        """Delegate to RulesContentRenderer."""
        return self._renderer.render(metadata, rules_by_category, readme_content)

    def _format_priority_areas(self, areas: List[str]) -> str:
        """Delegate to RulesContentRenderer."""
        return self._renderer._format_priority_areas(areas)

    def _validate_quality(
        self,
        content: str,
        metadata: RulesMetadata,
        rules_by_category: Dict[str, List[Rule]],
    ) -> QualityReport:
        """Delegate to RulesQualityValidator."""
        return self._quality_validator.validate(content, metadata, rules_by_category)

    def _detect_rule_conflicts(self, rules_by_category: Dict[str, List[Rule]]) -> List[str]:
        """Delegate to RulesQualityValidator."""
        return self._quality_validator._detect_rule_conflicts(rules_by_category)

    def _check_git_available(self) -> bool:
        """Delegate to RulesGitMiner."""
        return self._git_miner.available

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

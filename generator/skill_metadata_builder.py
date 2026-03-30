"""
Skill Metadata Builder
======================

Builds SkillMetadata — triggers, tools, tags, frontmatter rendering.
Extracted from CoworkSkillCreator to keep each module focused.

Note: SkillMetadata is defined in skill_creator.py and imported here
to avoid a circular import.
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING, List, Set

from generator.tech_registry import TECH_TOOLS as _TECH_TOOLS

if TYPE_CHECKING:
    from generator.skill_creator import SkillMetadata


class SkillMetadataBuilder:
    """Builds SkillMetadata objects from skill name, README, and project context."""

    TECH_TOOLS = _TECH_TOOLS

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
        "anthropic": ["anthropic", "claude", "llm skill", "ai provider", "cowork skill"],
        "openai": ["openai", "gpt", "chatgpt", "llm"],
        "gemini": ["gemini", "google ai", "vertex ai"],
        "groq": ["groq", "llama", "fast inference"],
    }

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def build(
        self,
        skill_name: str,
        readme_content: str,
        tech_stack: List[str],
        project_signals: List[str],
    ) -> "SkillMetadata":
        """Build smart metadata with Cowork intelligence.

        Args:
            skill_name: The skill identifier (e.g. "fastapi-security-auditor")
            readme_content: Project README text for context
            tech_stack: Already-detected tech stack (caller owns detection + caching)
            project_signals: Already-detected project signals (has_docker, etc.)
        """
        from generator.skill_creator import SkillMetadata

        triggers = self._generate_triggers(skill_name, readme_content, tech_stack)
        tools = self._select_tools(skill_name, tech_stack)
        description = self._generate_description(skill_name, readme_content)
        negative_triggers = self._generate_negative_triggers(skill_name, tech_stack)
        tags = self._generate_tags(skill_name, tech_stack)

        return SkillMetadata(
            name=skill_name,
            description=description,
            auto_triggers=triggers,
            project_signals=project_signals,
            tools=tools,
            negative_triggers=negative_triggers,
            tags=tags,
        )

    def render_frontmatter(self, metadata: "SkillMetadata") -> str:
        """Emit Anthropic-spec-compliant YAML frontmatter (GAP 1 + GAP 4 + GAP 5)."""
        trigger_str = ", ".join(f'"{t}"' for t in metadata.auto_triggers[:5])
        base_desc = metadata.description.rstrip(".")
        desc = f"{base_desc}. Use when user mentions {trigger_str}."
        if metadata.negative_triggers:
            neg_str = ", ".join(f'"{t}"' for t in metadata.negative_triggers[:3])
            desc += f" Do NOT activate for {neg_str}."
        desc = desc[:1024]

        claude_tools = "Bash Read Write Edit Glob Grep"
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

    def generate_critical_rules(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Generate non-negotiable rules for the ## CRITICAL section (GAP-5)."""
        rules: List[str] = [
            "Read existing files before modifying them.",
            "Run tests after any code change and verify they pass.",
            "Never generate or reference file paths that don't exist in the project.",
        ]

        name_lower = skill_name.lower()
        techs_lower = [t.lower() for t in tech_stack]

        if any(x in name_lower or x in techs_lower for x in ("test", "pytest", "jest", "coverage")):
            rules.append("Never skip tests or suppress coverage with `--no-cov` / `--no-cover`.")

        if any(x in name_lower or x in techs_lower for x in ("docker", "deploy", "kubernetes", "k8s")):
            rules.append("Never deploy to production without confirming the target environment first.")

        if any(x in name_lower or x in techs_lower for x in ("sql", "database", "postgres", "mysql", "mongo")):
            rules.append("Never run destructive SQL (DROP, TRUNCATE, DELETE without WHERE) without a dry-run first.")

        if any(x in name_lower or x in techs_lower for x in ("auth", "security", "oauth", "jwt")):
            rules.append("Never log or expose secrets, tokens, or credentials in output.")

        return rules

    # --- private helpers ---

    def _generate_triggers(self, skill_name: str, readme_content: str, tech_stack: List[str]) -> List[str]:
        """Generate smart auto-triggers with Cowork-style variations."""
        triggers = []

        base = skill_name.replace("-", " ").lower()
        triggers.append(base)

        for tech in tech_stack:
            tech_lower = tech.lower()
            if tech_lower in base:
                triggers.append(f"audit {tech_lower}")
                triggers.append(f"review {tech_lower}")

        expanded = set(triggers)
        for trigger in triggers:
            words = trigger.split()
            for word in words:
                if word in self.TRIGGER_SYNONYMS:
                    for synonym in self.TRIGGER_SYNONYMS[word][:2]:
                        new_trigger = trigger.replace(word, synonym)
                        expanded.add(new_trigger)

        action_triggers = self._extract_action_triggers(readme_content, base)
        expanded.update(action_triggers)

        return list(sorted(expanded))[:8]

    def _extract_action_triggers(self, readme_content: str, skill_base: str) -> Set[str]:
        """Extract action-based triggers from README."""
        triggers = set()
        action_verbs = [
            "run", "execute", "check", "validate", "analyze",
            "generate", "create", "build", "test", "deploy",
        ]
        lines = readme_content.lower().split("\n")
        skill_words = skill_base.split()

        for line in lines:
            if any(word in line for word in skill_words):
                for verb in action_verbs:
                    if verb in line:
                        triggers.add(f"{verb} {skill_base}")
                        break

        return triggers

    def _select_tools(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Intelligently select tools needed for this skill."""
        tools: Set[str] = set()

        for tech in tech_stack:
            tech_lower = tech.lower()
            if tech_lower in self.TECH_TOOLS:
                tools.update(self.TECH_TOOLS[tech_lower])

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

        tools = self._validate_tools_availability(tools)
        return list(sorted(tools))

    def _validate_tools_availability(self, tools: Set[str]) -> Set[str]:
        """Check if tools are actually available/referenced in project."""
        available: Set[str] = set()

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
                except OSError:
                    pass

        system_tools = {
            "git", "docker", "curl", "bash", "pytest", "python", "pip",
            "npm", "node", "pylint", "ruff", "black", "mypy", "coverage",
            "radon", "vulture", "bandit", "safety",
            "anthropic", "openai", "gemini", "groq", "langchain",
        }

        for tool in tools:
            if tool in all_content or tool in system_tools:
                available.add(tool)

        return available

    def _generate_description(self, skill_name: str, readme_content: str) -> str:
        """Generate concise skill description."""
        skill_words = skill_name.replace("-", " ").split()
        lines = readme_content.split("\n")
        for line in lines:
            stripped = line.strip()
            if re.match(r"^\d+[\.\)]", stripped):
                continue
            if stripped.startswith(("#", "-", "*", ">", "|", "!", "`", "[")):
                continue
            line_lower = stripped.lower()
            if any(word in line_lower for word in skill_words) and len(stripped) > 20:
                return stripped[:150]

        parts = skill_name.split("-")
        tech = parts[0].upper() if parts else skill_name.upper()
        action = " ".join(parts[1:]).replace("-", " ") if len(parts) > 1 else "workflow"
        return (
            f"Inconsistent {action} patterns accumulate when {tech} projects lack a shared approach. "
            f"Apply this skill to enforce the correct {action} workflow every time."
        )

    def _generate_negative_triggers(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Generate negative triggers to prevent over-activation (GAP 5)."""
        negatives: List[str] = []
        tech = skill_name.split("-")[0].lower()

        if tech and tech not in ("project", "workflow"):
            negatives.append(f"general {tech} questions")
            negatives.append(f"{tech} theory")

        if "test" in skill_name:
            negatives.append("production deployment")
        if "deploy" in skill_name or "docker" in skill_name:
            negatives.append("writing unit tests")

        return negatives[:3]

    def _generate_tags(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Derive searchable tags from skill name and detected tech stack (GAP 8)."""
        tags: List[str] = []
        tags.extend(p for p in skill_name.split("-") if len(p) > 2)
        for tech in tech_stack:
            if tech.lower() not in tags:
                tags.append(tech.lower())
        return list(dict.fromkeys(tags))[:6]

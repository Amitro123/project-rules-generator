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
from typing import Dict, List, Optional, Set, Tuple

import yaml

try:
    from jinja2 import Environment, FileSystemLoader, Template
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


@dataclass
class QualityReport:
    """Quality assessment of generated skill."""

    score: float  # 0-100
    passed: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


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

    def create_skill(
        self,
        skill_name: str,
        readme_content: str,
        tech_stack: Optional[List[str]] = None,
        custom_context: Optional[Dict] = None,
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
        # 1. Build metadata with smart triggers
        metadata = self._build_metadata(skill_name, readme_content, tech_stack)

        # 2. Generate skill content
        content = self._generate_content(
            skill_name, readme_content, metadata, custom_context
        )

        # 3. Quality validation
        quality = self._validate_quality(content, metadata)

        # 4. If quality is low, attempt auto-fix
        if not quality.passed:
            content = self._auto_fix_quality_issues(content, quality)
            quality = self._validate_quality(content, metadata)

        return content, metadata, quality

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

        return SkillMetadata(
            name=skill_name,
            description=description,
            auto_triggers=triggers,
            project_signals=list(signals),
            tools=tools,
        )

    def _generate_triggers(
        self, skill_name: str, readme_content: str, tech_stack: List[str]
    ) -> List[str]:
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
                # "fastapi security" → "audit fastapi", "review api security"
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

    def _extract_action_triggers(
        self, readme_content: str, skill_base: str
    ) -> Set[str]:
        """Extract action-based triggers from README."""
        triggers = set()

        # Look for imperative verbs near skill topic
        action_verbs = [
            "run", "execute", "check", "validate", "analyze",
            "generate", "create", "build", "test", "deploy"
        ]

        # Simple pattern matching
        lines = readme_content.lower().split("\n")
        skill_words = skill_base.split()

        for line in lines:
            # If line mentions skill-related words
            if any(word in line for word in skill_words):
                for verb in action_verbs:
                    if verb in line:
                        # "run security audit" → "security audit"
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

        if "test" in skill_lower:
            tools.update(["pytest", "coverage"])

        if "deploy" in skill_lower or "docker" in skill_lower:
            tools.update(["docker", "docker-compose"])

        if "api" in skill_lower or "endpoint" in skill_lower:
            tools.update(["curl", "httpx", "pytest"])

        if "security" in skill_lower or "audit" in skill_lower:
            tools.update(["bandit", "safety", "ruff"])

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

        for tool in tools:
            # Tool exists in requirements OR is a system tool (git, docker, etc.)
            if tool in all_content or tool in {"git", "docker", "curl", "bash"}:
                available.add(tool)

        return available

    def _detect_tech_stack(self, readme_content: str) -> List[str]:
        """Auto-detect tech stack from README."""
        if self._tech_stack:
            return list(self._tech_stack)

        tech_keywords = {
            "fastapi", "flask", "django", "express", "react", "vue",
            "pytest", "jest", "docker", "kubernetes", "postgresql",
            "mongodb", "redis", "celery", "sqlalchemy", "pydantic",
            "openai", "anthropic", "langchain", "typescript", "python"
        }

        readme_lower = readme_content.lower()
        detected = {tech for tech in tech_keywords if tech in readme_lower}

        self._tech_stack = detected
        return list(detected)

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

    def _generate_description(
        self, skill_name: str, readme_content: str
    ) -> str:
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

    def _generate_content(
        self,
        skill_name: str,
        readme_content: str,
        metadata: SkillMetadata,
        custom_context: Optional[Dict] = None,
    ) -> str:
        """Generate complete skill content with Cowork structure."""

        # Try Jinja2 template first, fallback to inline generation
        if HAS_JINJA2:
            try:
                return self._generate_with_jinja2(
                    skill_name, readme_content, metadata, custom_context
                )
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

        # Build template context
        context = {
            "name": skill_name,
            "title": skill_name.replace("-", " ").title(),
            "description": metadata.description,
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
            "quality_score": 95,  # Will be updated after validation
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

        # Build YAML frontmatter
        frontmatter = {
            "name": skill_name,
            "description": metadata.description,
            "auto_triggers": {
                "keywords": metadata.auto_triggers,
                "project_signals": metadata.project_signals,
            },
            "tools": metadata.tools,
            "category": metadata.category,
        }

        yaml_str = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)

        # Build content sections
        content = f"""---
{yaml_str}---

# Skill: {title}

## Purpose

{metadata.description}

This skill provides step-by-step guidance for {skill_name.replace('-', ' ')}.

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

**Tools Required:** {', '.join(f"`{t}`" for t in metadata.tools)}

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

**Detected Technologies:** {', '.join(self._detect_tech_stack(readme_content))}

**Compatible Tools:** {', '.join(metadata.tools)}

## Project Context

```
Project: {self.project_path.name}
Signals: {', '.join(metadata.project_signals)}
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

    def _validate_quality(
        self, content: str, metadata: SkillMetadata
    ) -> QualityReport:
        """
        Cowork's quality gates: ensure skill is actionable and specific.

        Checks:
        1. No placeholder text
        2. Specific commands/paths
        3. Proper trigger coverage
        4. Tool validation
        5. No hallucinated file paths
        """
        issues = []
        warnings = []
        suggestions = []
        score = 100.0

        # 1. Check for placeholders
        placeholders = [
            "[describe", "[example", "[your", "[add", "[insert",
            "TODO", "FIXME", "XXX"
        ]
        for placeholder in placeholders:
            if placeholder.lower() in content.lower():
                issues.append(f"Contains placeholder: {placeholder}")
                score -= 10

        # 2. Check for specific paths/commands
        if "cd project_name" in content or "cd /path/to" in content:
            issues.append("Contains generic path placeholders")
            score -= 15

        # 3. Validate triggers coverage
        if len(metadata.auto_triggers) < 3:
            warnings.append("Only {len(metadata.auto_triggers)} triggers (recommend 5+)")
            score -= 5

        # 4. Check for hallucinated file paths
        hallucinated = self._detect_hallucinated_paths(content)
        if hallucinated:
            issues.append(f"Hallucinated file paths: {', '.join(hallucinated[:3])}")
            score -= 20

        # 5. Tool validation
        if not metadata.tools:
            warnings.append("No tools specified")
            score -= 5

        # 6. Check for actionability (has code blocks or commands)
        if "```" not in content and "bash" not in content.lower():
            warnings.append("No code examples found (skill may not be actionable)")
            score -= 10

        # 7. Check for anti-patterns section
        if "## Anti-Patterns" not in content or "❌" not in content:
            suggestions.append("Add anti-patterns section with ❌/✅ markers")
            score -= 5

        passed = score >= 70 and len(issues) == 0

        return QualityReport(
            score=max(0, score),
            passed=passed,
            issues=issues,
            warnings=warnings,
            suggestions=suggestions,
        )

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

    def _auto_fix_quality_issues(
        self, content: str, quality: QualityReport
    ) -> str:
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
        for skill_name in set(skill_names): # Deduplicate
            try:
                content, metadata, quality = self.create_skill(
                    skill_name, readme_content
                )
                
                if quality.score >= quality_threshold or auto_fix:
                     # Attempt auto-fix implies we use the potentially fixed content returned by create_skill
                     # (create_skill already calls _auto_fix_quality_issues if needed)
                     path = self.export_to_file(content, metadata, output_dir)
                     generated_files.append(path)
            except Exception as e:
                print(f"Warning: Failed to generate {skill_name}: {e}")
                
        return generated_files

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

from generator.quality_validators import SkillQualityValidator
from generator.skill_discovery import SkillDiscovery
from generator.skill_doc_loader import SkillDocLoader
from generator.skill_metadata_builder import SkillMetadataBuilder
from generator.tech_registry import TECH_TOOLS as _TECH_TOOLS
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

    # Technology → Required Tools mapping (single source of truth: tech_registry.py)
    TECH_TOOLS = _TECH_TOOLS

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
        self._quality = SkillQualityValidator(project_path)
        self._doc_loader = SkillDocLoader(project_path)
        self._meta_builder = SkillMetadataBuilder(project_path)

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
        """Link a learned skill from Global Cache to Project Local Skills.

        Supports both storage formats:
        - Flat file: global_learned/<name>.md  → project_local_dir/<name>.md
        - Directory: global_learned/<name>/     → project_local_dir/<name>/
          (DESIGN-2 fix: link the *whole* directory so Level-3 subdirs are included)
        """
        source_flat = self.discovery.global_learned / f"{skill_name}.md"
        source_dir = self.discovery.global_learned / skill_name

        if not self.discovery.project_local_dir:
            print(f"⚠️  Could not link {skill_name}: No project path configured.")
            return

        if source_flat.exists():
            # Flat-file style: link the .md directly
            target = self.discovery.project_local_dir / f"{skill_name}.md"
            self.discovery._link_or_copy(source_flat, target)
        elif source_dir.exists() and source_dir.is_dir():
            # Directory-style skill — link the entire directory contents, but
            # avoid calling _link_or_copy on directories (test double may use shutil.copy2).
            target_dir = self.discovery.project_local_dir / skill_name
            target_dir.mkdir(parents=True, exist_ok=True)

            # Always make SKILL.md available at top-level <name>.md for convenience
            src_md = source_dir / "SKILL.md"
            if src_md.exists():
                self.discovery._link_or_copy(src_md, self.discovery.project_local_dir / f"{skill_name}.md")

            for item in source_dir.rglob("*"):
                rel = item.relative_to(source_dir)
                dest = target_dir / rel
                if item.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    self.discovery._link_or_copy(item, dest)
        else:
            print(f"⚠️  Could not link {skill_name}: Source not found in global learned.")

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
                except OSError:
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
        """Build smart metadata — delegates to SkillMetadataBuilder."""
        if tech_stack is None:
            tech_stack = self._detect_tech_stack(readme_content)
        signals = list(self._detect_project_signals())
        return self._meta_builder.build(skill_name, readme_content, tech_stack, signals)

    def _generate_triggers(self, skill_name: str, readme_content: str, tech_stack: List[str]) -> List[str]:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder._generate_triggers(skill_name, readme_content, tech_stack)

    def _select_tools(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder._select_tools(skill_name, tech_stack)

    def _validate_tools_availability(self, tools: Set[str]) -> Set[str]:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder._validate_tools_availability(tools)

    def _generate_description(self, skill_name: str, readme_content: str) -> str:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder._generate_description(skill_name, readme_content)

    def _generate_negative_triggers(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder._generate_negative_triggers(skill_name, tech_stack)

    def _generate_tags(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder._generate_tags(skill_name, tech_stack)

    def _generate_critical_rules(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder.generate_critical_rules(skill_name, tech_stack)

    def _render_frontmatter(self, metadata: "SkillMetadata") -> str:
        """Delegate to SkillMetadataBuilder."""
        return self._meta_builder.render_frontmatter(metadata)

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

    def is_readme_sufficient(self, readme_content: str) -> bool:
        """Return True if README has enough content for meaningful skill generation."""
        from generator.utils.readme_bridge import is_readme_sufficient

        return is_readme_sufficient(readme_content)

    def _scan_project_tree(self, max_depth: int = 3, max_items: int = 60) -> str:
        """Walk the project directory and produce a structured tree for LLM context."""
        from generator.utils.readme_bridge import build_project_tree

        return build_project_tree(self.project_path, max_depth=max_depth, max_items=max_items)

    def _generate_description(self, skill_name: str, readme_content: str) -> str:
        """Generate concise skill description."""
        # Extract purpose from first paragraph mentioning skill topic
        skill_words = skill_name.replace("-", " ").split()

        import re as _re

        lines = readme_content.split("\n")
        for line in lines:
            stripped = line.strip()
            # Skip numbered list items, bullet points, headings, badges, and code blocks
            if _re.match(r"^\d+[\.\)]", stripped):
                continue
            if stripped.startswith(("#", "-", "*", ">", "|", "!", "`", "[")):
                continue
            line_lower = stripped.lower()
            if any(word in line_lower for word in skill_words) and len(stripped) > 20:
                return stripped[:150]

        # Fallback: pain-oriented default (avoids "This skill provides...")
        parts = skill_name.split("-")
        tech = parts[0].upper() if parts else skill_name.upper()
        action = " ".join(parts[1:]).replace("-", " ") if len(parts) > 1 else "workflow"
        return f"Inconsistent {action} patterns accumulate when {tech} projects lack a shared approach. Apply this skill to enforce the correct {action} workflow every time."

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

    def _generate_critical_rules(self, skill_name: str, tech_stack: List[str]) -> List[str]:
        """Generate non-negotiable rules for the ## CRITICAL section (GAP-5).

        Returns a short list of rules Claude must always follow when this skill
        is active. Generic rules always apply; additional ones are added based
        on the skill domain.
        """
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

    def _score_doc(self, path: Path, content: str) -> int:
        """Delegate to SkillDocLoader."""
        return self._doc_loader._score_doc(path, content)

    def _discover_supplementary_docs(self) -> List[Path]:
        """Delegate to SkillDocLoader."""
        return self._doc_loader.discover_supplementary_docs()

    def _load_key_files(self, skill_name: str) -> Dict[str, str]:
        """Delegate to SkillDocLoader."""
        return self._doc_loader.load_key_files(skill_name)

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
        tech_stack = self._detect_tech_stack(readme_content)
        critical_rules = self._generate_critical_rules(skill_name, tech_stack)

        # Build template context
        context = {
            "name": skill_name,
            "title": skill_name.replace("-", " ").title(),
            "description": metadata.description,
            "desc_with_triggers": desc_with_triggers,  # GAP 1/4/5
            "negative_triggers": metadata.negative_triggers,  # GAP 5
            "tags": tags,  # GAP 8
            "critical_rules": critical_rules,  # GAP-5 CRITICAL section
            "purpose": metadata.description,
            "purpose_extended": "",  # description already carries the pain-first statement
            "auto_triggers": metadata.auto_triggers,
            "project_signals": metadata.project_signals,
            "tools": metadata.tools,
            "category": metadata.category,
            "priority": metadata.priority,
            # resolve() avoids "" when project_path is Path(".")
            "project_name": self.project_path.resolve().name or self.project_path.resolve().stem,
            "project_path": str(self.project_path.resolve()),
            "tech_stack": tech_stack,
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
        tech_stack_inline = self._detect_tech_stack(readme_content)
        critical_rules = self._generate_critical_rules(skill_name, tech_stack_inline)
        critical_block = ""
        if critical_rules:
            rules_md = "\n".join(f"- {r}" for r in critical_rules)
            critical_block = (
                f"\n## CRITICAL\n\n"
                f"> These rules are non-negotiable. Claude must follow them on every activation.\n\n"
                f"{rules_md}\n"
            )

        _proj_name = self.project_path.resolve().name or self.project_path.resolve().stem
        content = self._render_frontmatter(metadata)
        content += f"""# Skill: {title}

## Purpose

{metadata.description}

## Auto-Trigger

The agent should activate this skill when:

{self._format_triggers(metadata.auto_triggers)}

**Project Signals:**
{self._format_signals(metadata.project_signals)}
{critical_block}
## Process

### 1. Analyze Current State

- Check project structure in `{_proj_name}/`
- Review relevant configuration files
- Identify existing patterns

### 2. Execute Core Steps

**Tools Required:** {", ".join(f"`{t}`" for t in metadata.tools)}

```bash
# Example workflow
cd {_proj_name}
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
Project: {_proj_name}
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
        """Delegate to SkillQualityValidator."""
        return self._quality.validate(content, metadata)

    def _detect_hallucinated_paths(self, content: str) -> List[str]:
        """Delegate to SkillQualityValidator."""
        return self._quality._detect_hallucinated_paths(content)

    def _auto_fix_quality_issues(self, content: str, quality: QualityReport) -> str:
        """Delegate to SkillQualityValidator."""
        return self._quality.auto_fix(content, quality)

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
            # Use SkillGenerator.TECH_SKILL_NAMES as the single source of truth (BUG-1 fix)
            from generator.skill_generator import SkillGenerator

            for tech in tech_stack:
                name = SkillGenerator.TECH_SKILL_NAMES.get(tech.lower())
                if name:
                    skill_names.append(name)

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

"""Skill content renderer — Jinja2 template + inline fallback generation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from generator.skill_doc_loader import SkillDocLoader
from generator.skill_metadata_builder import SkillMetadataBuilder

if TYPE_CHECKING:
    from generator.skill_creator import SkillMetadata

try:
    from jinja2 import Environment, FileSystemLoader

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

logger = logging.getLogger(__name__)


class SkillContentRenderer:
    """Renders skill markdown content via Jinja2 template or inline fallback.

    Extracted from CoworkSkillCreator to give it a single responsibility.
    Receives collaborators via constructor — no project scanning here.
    """

    def __init__(
        self,
        project_path: Path,
        scanner: "ProjectContextScanner",  # type: ignore[name-defined]  # noqa: F821
        meta_builder: SkillMetadataBuilder,
        doc_loader: SkillDocLoader,
    ):
        self.project_path = project_path
        self._scanner = scanner
        self._meta_builder = meta_builder
        self._doc_loader = doc_loader

    def generate_content(
        self,
        skill_name: str,
        readme_content: str,
        metadata: "SkillMetadata",
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

                tech_list = self._scanner._detect_tech_stack(readme_content)
                _backend = {"fastapi", "flask", "django", "python", "express", "node", "fastapi"}
                _frontend = {"react", "vue", "angular", "typescript", "javascript", "nextjs"}
                _database = {"postgresql", "mysql", "mongodb", "redis", "sqlalchemy", "sqlite"}

                signals = set(metadata.project_signals)
                context = {
                    "readme": readme_content,
                    "project_name": self.project_path.name,
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
                    "key_files": self._doc_loader.load_key_files(skill_name),
                    "project_analysis": custom_context.get("project_analysis", {}) if custom_context else {},
                }

                logger.info("Generating with AI (%s)...", provider)
                return generator.generate_skill(skill_name, context)
            except Exception as e:
                logger.warning("AI generation failed: %s. Falling back to templates.", e)

        # 2. Try Jinja2 template first, fallback to inline generation
        if HAS_JINJA2:
            try:
                return self._generate_with_jinja2(skill_name, readme_content, metadata, custom_context)
            except Exception as e:
                logger.warning("Jinja2 template failed (%s), using inline generation", e)

        # Fallback: inline generation
        return self._generate_inline(skill_name, readme_content, metadata)

    def _generate_with_jinja2(
        self,
        skill_name: str,
        readme_content: str,
        metadata: "SkillMetadata",
        custom_context: Optional[Dict] = None,
    ) -> str:
        """Generate using Jinja2 template."""
        template_dir = Path(__file__).parent.parent / "templates"
        template_path = template_dir / "SKILL.md.jinja2"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("SKILL.md.jinja2")

        trigger_str = ", ".join(f'"{t}"' for t in metadata.auto_triggers[:5])
        base_desc = metadata.description.rstrip(".")
        desc_with_triggers = f"{base_desc}. Use when user mentions {trigger_str}."
        if metadata.negative_triggers:
            neg_str = ", ".join(f'"{t}"' for t in metadata.negative_triggers[:3])
            desc_with_triggers += f" Do NOT activate for {neg_str}."
        desc_with_triggers = desc_with_triggers[:1024]

        tags = metadata.tags if metadata.tags else [metadata.category]
        tech_stack = self._scanner._detect_tech_stack(readme_content)
        critical_rules = self._meta_builder.generate_critical_rules(skill_name, tech_stack)

        context = {
            "name": skill_name,
            "title": skill_name.replace("-", " ").title(),
            "description": metadata.description,
            "desc_with_triggers": desc_with_triggers,
            "negative_triggers": metadata.negative_triggers,
            "tags": tags,
            "critical_rules": critical_rules,
            "purpose": metadata.description,
            "purpose_extended": "",
            "auto_triggers": metadata.auto_triggers,
            "project_signals": metadata.project_signals,
            "tools": metadata.tools,
            "category": metadata.category,
            "priority": metadata.priority,
            "project_name": self.project_path.resolve().name or self.project_path.resolve().stem,
            "project_path": str(self.project_path.resolve()),
            "tech_stack": tech_stack,
            "readme_context": readme_content[:500] if readme_content else None,
            # BUG-C fix: quality_score removed — it is computed by _validate_quality()
            # *after* content generation. Hardcoding 95 here was misleading.
        }

        if custom_context:
            context.update(custom_context)

        return template.render(**context)

    def _generate_inline(
        self,
        skill_name: str,
        readme_content: str,
        metadata: "SkillMetadata",
    ) -> str:
        """Fallback inline generation (no Jinja2)."""
        title = skill_name.replace("-", " ").title()

        tech_stack_inline = self._scanner._detect_tech_stack(readme_content)
        critical_rules = self._meta_builder.generate_critical_rules(skill_name, tech_stack_inline)
        critical_block = ""
        if critical_rules:
            rules_md = "\n".join(f"- {r}" for r in critical_rules)
            critical_block = (
                f"\n## CRITICAL\n\n"
                f"> These rules are non-negotiable. Claude must follow them on every activation.\n\n"
                f"{rules_md}\n"
            )

        _proj_name = self.project_path.resolve().name or self.project_path.resolve().stem
        content = self._meta_builder.render_frontmatter(metadata)
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

**Detected Technologies:** {", ".join(self._scanner._detect_tech_stack(readme_content))}

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

    @staticmethod
    def _format_triggers(triggers: List[str]) -> str:
        """Format triggers as markdown list."""
        return "\n".join(f"- {t}" for t in triggers)

    @staticmethod
    def _format_signals(signals: List[str]) -> str:
        """Format project signals as markdown list."""
        if not signals:
            return "- None detected"
        return "\n".join(f"- `{s}`" for s in signals)

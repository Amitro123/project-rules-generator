"""Stub template strategy for skill generation (fallback)."""

from pathlib import Path
from typing import Optional


class StubStrategy:
    """Generate generic stub template - always succeeds as final fallback."""

    def generate(
        self,
        skill_name: str,
        project_path: Optional[Path],
        from_readme: Optional[str],
        provider: str,
        **kwargs: object,
    ) -> str:
        """
        Generate stub template with placeholders.

        Returns:
            Always returns a valid stub template (never None)
        """
        additional_context = ""

        # from_readme is already normalised to *content* by skill_generator.py
        if from_readme:
            additional_context = f"\n\n## Context (from README)\n\n{from_readme[:400]}\n"

        title = skill_name.replace("-", " ").title()
        content = (
            f"# Skill: {title}\n\n"
            f"## Purpose\n[One sentence: what problem does this solve]\n\n"
            f"## Auto-Trigger\n[When should agent activate this skill]\n\n"
            f"## Process\n[Step-by-step instructions]\n\n"
            f"## Output\n[What artifact/state results]\n\n"
            f"## Anti-Patterns\n❌ [What NOT to do]\n"
        )

        return content + additional_context

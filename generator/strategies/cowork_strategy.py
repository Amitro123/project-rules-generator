"""Cowork analysis strategy for skill generation."""

import logging
from pathlib import Path
from typing import Optional

from generator.utils.readme_bridge import bridge_missing_context, is_readme_sufficient


class CoworkStrategy:
    """Generate skills using Cowork's intelligent project analysis."""

    def generate(
        self,
        skill_name: str,
        project_path: Optional[Path],
        from_readme: Optional[str],
        provider: str,
    ) -> Optional[str]:
        """
        Generate skill using CoworkSkillCreator with project analysis.

        If the README is missing or too sparse, supplements it with:
        - The project directory tree (always)
        - A user-provided description (CLI/interactive mode)
        - Or lets the AI infer from structure alone (non-interactive / IDE mode)

        Returns:
            Generated skill content or None if generation fails
        """
        if not project_path:
            return None

        try:
            from generator.skill_creator import CoworkSkillCreator

            logging.info("📚 Using Cowork analysis for '%s'...", skill_name)
            creator = CoworkSkillCreator(Path(project_path))
            readme_content = from_readme or ""

            # If README is insufficient, bridge the gap before generating
            if not is_readme_sufficient(readme_content):
                supplement = bridge_missing_context(Path(project_path), skill_name)
                if supplement:
                    readme_content = supplement + "\n\n" + readme_content

            content, metadata, quality = creator.create_skill(
                skill_name, readme_content, use_ai=False, provider=provider
            )
            logging.info("✅ Cowork quality score: %s/100", quality.score)
            return content

        except Exception as e:
            logging.warning("[!] Cowork fallback failed (%s). Using stub template.", e)
            return None

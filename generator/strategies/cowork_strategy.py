"""Cowork analysis strategy for skill generation."""

from pathlib import Path
from typing import Optional


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
        
        Returns:
            Generated skill content or None if Cowork generation fails
        """
        if not project_path:
            return None
            
        try:
            from generator.skill_creator import CoworkSkillCreator
            
            print(f"📚 Using Cowork analysis for '{skill_name}'...")
            creator = CoworkSkillCreator(Path(project_path))
            content, metadata, quality = creator.create_skill(
                skill_name, from_readme or ""
            )
            print(f"✅ Cowork quality score: {quality.score}/100")
            return content
        except Exception as e:
            print(f"[!] Warning: Cowork fallback failed ({e}). Using stub template.")
            return None

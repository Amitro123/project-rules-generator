"""Base protocol for skill generation strategies."""

from pathlib import Path
from typing import Optional, Protocol


class SkillGenerationStrategy(Protocol):
    """Protocol defining the interface for skill generation strategies."""
    
    def generate(
        self,
        skill_name: str,
        project_path: Optional[Path],
        from_readme: Optional[str],
        provider: str,
    ) -> Optional[str]:
        """
        Generate skill content using this strategy.
        
        Args:
            skill_name: Name of the skill to generate
            project_path: Path to the project (for context analysis)
            from_readme: Path to README file (for parsing)
            provider: AI provider name (e.g., "groq", "gemini")
        
        Returns:
            Skill content as markdown string if successful, None if strategy doesn't apply
        """
        ...

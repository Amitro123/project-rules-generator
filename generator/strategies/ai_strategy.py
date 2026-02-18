"""AI-based skill generation strategy using LLM providers."""

from pathlib import Path
from typing import Optional


class AIStrategy:
    """Generate skills using AI (LLM) providers like Groq or Gemini."""
    
    def generate(
        self,
        skill_name: str,
        project_path: Optional[Path],
        from_readme: Optional[str],
        provider: str,
    ) -> Optional[str]:
        """
        Generate skill content using AI provider.
        
        Returns:
            Generated skill content or None if AI generation fails
        """
        if not project_path:
            return None
            
        try:
            from generator.llm_skill_generator import LLMSkillGenerator
            from generator.project_analyzer import ProjectAnalyzer
            
            print(f"🤖 Analyzing project context in {project_path}...")
            analyzer = ProjectAnalyzer(Path(project_path))
            context = analyzer.analyze()
            
            print(f"✨ Generating skill with AI ({provider})...")
            generator = LLMSkillGenerator(provider=provider)
            return generator.generate_skill(skill_name, context)
        except ImportError as e:
            print(f"[!] Warning: AI provider not available ({e}). Falling back to next strategy.")
            return None
        except Exception as e:
            print(f"[!] Warning: AI generation failed ({e}). Falling back to next strategy.")
            return None

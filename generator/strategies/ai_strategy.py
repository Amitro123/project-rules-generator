"""AI-based skill generation strategy using LLM providers."""

import concurrent.futures
from pathlib import Path
from typing import Optional

# How long (seconds) to allow ProjectAnalyzer.analyze() to run before giving up.
# Large repos with deep directory trees can stall the strategy chain indefinitely.
_ANALYSIS_TIMEOUT_SECS = 10


class AIStrategy:
    """Generate skills using AI (LLM) providers like Groq, Gemini, Anthropic, or OpenAI."""

    def generate(
        self,
        skill_name: str,
        project_path: Optional[Path],
        from_readme: Optional[str],
        provider: str,
        strategy: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate skill content using AI provider or router.

        Args:
            strategy: Router strategy ("auto", "speed", "quality", "provider:X").
                      When set, AIStrategyRouter is used instead of a direct provider call.

        Returns:
            Generated skill content or None if AI generation fails.
        """
        if not project_path:
            return None

        try:
            from generator.llm_skill_generator import LLMSkillGenerator
            from generator.project_analyzer import ProjectAnalyzer

            print(f"🤖 Analyzing project context in {project_path}...")
            analyzer = ProjectAnalyzer(Path(project_path))

            # Run in a thread so a slow/large repo can't block the strategy chain forever.
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(analyzer.analyze)
                try:
                    context = future.result(timeout=_ANALYSIS_TIMEOUT_SECS)
                except concurrent.futures.TimeoutError:
                    print(
                        f"[!] Warning: ProjectAnalyzer timed out after {_ANALYSIS_TIMEOUT_SECS}s "
                        f"(large repo?). Falling back to next strategy."
                    )
                    return None

            provider_label = f"router:{strategy}" if strategy else provider
            print(f"✨ Generating skill with AI ({provider_label})...")
            generator = LLMSkillGenerator(provider=provider, strategy=strategy)
            return generator.generate_skill(skill_name, context)
        except ImportError as e:
            print(f"[!] Warning: AI provider not available ({e}). Falling back to next strategy.")
            return None
        except Exception as e:
            print(f"[!] Warning: AI generation failed ({e}). Falling back to next strategy.")
            return None

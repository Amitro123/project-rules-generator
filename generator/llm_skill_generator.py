"""Generate skills using LLM with project context."""

import os
import re
from typing import Dict, List, Optional, Tuple

from .ai.factory import create_ai_client


def _parse_python_deps_from_files(key_files: Dict[str, str]) -> List[str]:
    """Extract package names from requirements.txt or pyproject.toml content in key_files."""
    deps: List[str] = []
    seen: set = set()

    req_content = key_files.get("requirements.txt", "")
    for line in req_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name = re.split(r"[>=<![\s]", line)[0].strip().lower()
            if name and name not in seen:
                seen.add(name)
                deps.append(name)

    pyproject_content = key_files.get("pyproject.toml", "")
    for line in pyproject_content.splitlines():
        m = re.match(r'^\s*"?([a-zA-Z0-9_-]+)"?\s*[=<>]', line)
        if m:
            name = m.group(1).lower()
            if name not in ("python", "pip") and name not in seen:
                seen.add(name)
                deps.append(name)

    return deps[:20]


def _detect_test_framework_from_files(key_files: Dict[str, str]) -> str:
    """Detect test framework from any key_files content."""
    combined = " ".join(key_files.values()).lower()
    if "pytest" in combined:
        return "pytest"
    if "jest" in combined or "vitest" in combined:
        return "jest"
    return ""


def _extract_readme_description(readme_text: str) -> str:
    """Return the first non-heading, non-badge, non-empty line of the README."""
    for line in readme_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("!") and not stripped.startswith("[!"):
            return stripped[:200]
    return ""


class LLMSkillGenerator:
    """Generate actionable skills using LLM analysis.

    Supports two modes:
    - Direct provider mode (legacy): pass ``provider`` to target a specific client.
    - Router mode: pass ``strategy`` ("auto", "speed", "quality", "provider:X")
      to let AIStrategyRouter pick the best available provider with fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: str = "groq",
        strategy: Optional[str] = None,
    ):
        self.provider = provider
        self.strategy = strategy  # None → direct mode; set → router mode
        self.model_name = model_name
        self.api_key: Optional[str]

        if strategy is not None:
            # Router mode — defer client creation to smart_generate
            self.client = None
            self.api_key = api_key
            return

        # Direct mode — original behaviour
        if api_key:
            self.api_key = api_key
        elif self.provider == "groq":
            self.api_key = os.getenv("GROQ_API_KEY")
        elif self.provider == "gemini":
            self.api_key = os.getenv("GEMINI_API_KEY")
        elif self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
        elif self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
        else:
            self.api_key = None

        try:
            self.client = create_ai_client(self.provider, api_key=self.api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize AI client ({self.provider}): {e}")

    def generate_skill(self, skill_name: str, context: Dict) -> str:
        """Generate complete skill from project context.

        DESIGN-2 fix: delegates to the canonical build_skill_prompt() from
        generator/prompts/skill_generation.py instead of the old _build_prompt()
        so all production paths produce skills in the same format.
        """
        from generator.prompts.skill_generation import build_skill_prompt

        # Flatten tech_stack dict → list
        tech = context.get("tech_stack", {})
        flat_tech: list = []
        for vals in tech.values():
            if isinstance(vals, list):
                flat_tech.extend(vals)
            elif isinstance(vals, str):
                flat_tech.append(vals)

        readme_text = context.get("readme", "")
        key_files = context.get("key_files", {})

        # Fix 1 (readme.description key): extract first prose line so _format_context
        # can populate the "Description:" line in the prompt.
        description = _extract_readme_description(readme_text)

        # Fix 3 (always-empty deps/tests): parse from key_files content.
        python_deps = _parse_python_deps_from_files(key_files)
        test_framework = _detect_test_framework_from_files(key_files)

        adapted_context: Dict = {
            "metadata": {
                "tech_stack": flat_tech,
                "project_name": context.get("project_name", ""),
            },
            "readme": {
                "description": description,
                "content": readme_text,
            },
            "structure": context.get("structure", {}),
            "dependencies": {"python": [{"name": d} for d in python_deps]},
            "test_patterns": {"framework": test_framework} if test_framework else {},
        }

        code_examples = [{"file": fname, "content": content[:400]} for fname, content in key_files.items()]

        structure = context.get("structure", {})
        detected_patterns = [k for k, v in structure.items() if v]

        # Fix 2 (project_name=""): read from context dict populated by the renderer.
        project_name = context.get("project_name", "")

        prompt = build_skill_prompt(
            skill_topic=skill_name,
            project_name=project_name,
            context=adapted_context,
            code_examples=code_examples,
            detected_patterns=detected_patterns,
        )
        return self.generate_content(prompt, max_tokens=4000)

    def generate_content(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate content from prompt using the configured model or router."""
        if self.strategy is not None:
            # Router mode: smart provider selection with fallback
            from generator.ai.ai_strategy_router import AIStrategyRouter

            router = AIStrategyRouter(strategy=self.strategy)
            try:
                content, used_provider = router.smart_generate(prompt, task_type="skills", max_tokens=max_tokens)
                self.provider = used_provider  # record which provider was chosen
                return content
            except Exception as e:
                raise RuntimeError(f"Router generation failed: {e}")
        # Direct mode (original behaviour)
        try:
            if self.client is None:
                return ""
            return self.client.generate(prompt, max_tokens=max_tokens, model=self.model_name)
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")

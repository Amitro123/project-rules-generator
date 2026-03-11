"""Generate skills using LLM with project context."""

import os
from typing import Dict, Optional, Tuple

from .ai.factory import create_ai_client


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
        """Generate complete skill from project context."""
        prompt = self._build_prompt(skill_name, context)
        return self.generate_content(prompt, max_tokens=2000)

    def generate_content(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate content from prompt using the configured model or router."""
        if self.strategy is not None:
            # Router mode: smart provider selection with fallback
            from generator.ai.ai_strategy_router import AIStrategyRouter

            router = AIStrategyRouter(strategy=self.strategy)
            try:
                content, used_provider = router.smart_generate(
                    prompt, task_type="skills", max_tokens=max_tokens
                )
                self.provider = used_provider  # record which provider was chosen
                return content
            except Exception as e:
                raise RuntimeError(f"Router generation failed: {e}")
        # Direct mode (original behaviour)
        try:
            return self.client.generate(prompt, max_tokens=max_tokens, model=self.model_name)
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")

    def _build_prompt(self, skill_name: str, context: Dict) -> str:
        """Build comprehensive prompt for LLM."""

        # Extract context
        readme = context.get("readme", "No README found")
        structure = context.get("structure", {})
        tech = context.get("tech_stack", {})
        key_files = context.get("key_files", {})

        # Build tech stack summary
        tech_summary = []
        if tech.get("backend"):
            tech_summary.append(f"**Backend**: {', '.join(tech['backend'])}")
        if tech.get("frontend"):
            tech_summary.append(f"**Frontend**: {', '.join(tech['frontend'])}")
        if tech.get("database"):
            tech_summary.append(f"**Database**: {', '.join(tech['database'])}")
        if tech.get("languages"):
            tech_summary.append(f"**Languages**: {', '.join(tech['languages'])}")

        tech_str = "\n".join(tech_summary) if tech_summary else "Tech stack not detected"

        # Build project structure summary
        structure_items = []
        if structure.get("has_backend"):
            structure_items.append("- Has `backend/` directory")
        if structure.get("has_frontend"):
            structure_items.append("- Has `frontend/` directory")
        if structure.get("has_api"):
            structure_items.append("- Has `api/` directory")
        if structure.get("has_tests"):
            structure_items.append("- Has `tests/` directory")
        if structure.get("has_docker"):
            structure_items.append("- Uses Docker")

        structure_str = "\n".join(structure_items) if structure_items else "Structure not analyzed"

        # Build key files snippets
        snippets = []
        for filename, content in key_files.items():
            if filename in [
                "api_sample",
                "main.py",
                "app.py",
                "settings.py",
                "config.py",
            ]:
                snippets.append(f"**{filename}**:\n```\n{content[:400]}\n```")

        snippets_str = "\n\n".join(snippets[:3]) if snippets else "No code samples available"

        prompt = f"""# Generate AI Agent Skill

## Skill Name
{skill_name.replace("-", " ").title()}

## Project Context

### README
{readme[:2000]}

### Tech Stack
{tech_str}

### Project Structure
{structure_str}

### Code Samples
{snippets_str}

***

## Your Task

Create a **complete, actionable skill** for an AI agent.

### Format:

```markdown
---
name: {skill_name.lower().replace(" ", "-")}
description: |
  [ONE sentence: what this skill does]. Use when user mentions "[keyword1]", "[keyword2]", "[keyword3]". Do NOT activate for "[unrelated topic]".
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  author: PRG
  version: 1.0.0
  category: [backend|frontend|testing|devops|project]
  tags: [[tag1, tag2, tag3]]
---

# Skill: {skill_name.replace("-", " ").title()}

## Purpose
[ONE clear sentence about what this solves in THIS project]

## Auto-Trigger

The agent should activate this skill when:
- [Trigger phrase 1]
- [Trigger phrase 2]
- [Trigger phrase 3]

## Process

### 1. [Step Name]
[Specific commands/actions for THIS project]

### 2. [Next Step]
[Continue with 3-7 steps]

## Output
- [Specific files/artifacts produced]
- [API responses]
- [Generated content]

## Anti-Patterns
❌ [Mistake #1] → [How to avoid]
❌ [Mistake #2] → [Correct approach]

## Tech Stack Notes
[Brief technical considerations]
```

### Requirements:
1. **Be SPECIFIC**: Use actual paths, commands, APIs from this project
2. **Be ACTIONABLE**: Agent should know exactly what to do
3. **No placeholders**: Fill in all sections with real content
4. **Anthropic-spec frontmatter**: description must embed trigger phrases using the exact format shown above
5. **No `auto_triggers` or `tools` YAML keys** — those are internal-only; the description field carries triggers

Generate the skill now:
"""

        return prompt

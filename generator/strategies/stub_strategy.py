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
        title = skill_name.replace("-", " ").title()
        skill_label = skill_name.replace("-", " ")
        parts = [p for p in skill_name.split("-") if len(p) > 2]
        trigger_str = ", ".join(f'"{t}"' for t in ([skill_label] + parts)[:3])

        content = (
            f"---\n"
            f"name: {skill_name}\n"
            f"description: |\n"
            f"  [One sentence: what this skill does and when to activate it.]\n"
            f"  Use when user mentions {trigger_str}.\n"
            f'allowed-tools: "Bash Read Write Edit Glob Grep"\n'
            f"triggers:\n"
            + "".join(f'  - "{t}"\n' for t in ([skill_label] + parts)[:3])
            + f"metadata:\n"
            f"  tags: [{', '.join(parts[:4])}]\n"
            f"---\n\n"
            f"# Skill: {title}\n\n"
            f"## Purpose\n\n"
            f"[One sentence: what problem does this solve and for whom.]\n\n"
            f"## Auto-Trigger\n\n"
            f"Activate when user requests:\n"
            + "".join(f'- **"{t}"**\n' for t in ([skill_label] + parts)[:3])
            + f"\nDo NOT activate for: [list false-positive phrases]\n\n"
            f"## Process\n\n"
            f"### 1. [First step]\n\n"
            f"```bash\n# command\n```\n\n"
            f"### 2. [Second step]\n\n"
            f"[description]\n\n"
            f"### 3. Validate\n\n"
            f"Verify the output is correct and tests still pass.\n\n"
            f"## Output\n\n"
            f"[What artifact or state results from applying this skill.]\n\n"
            f"## Anti-Patterns\n\n"
            f"❌ [What NOT to do]\n"
            f"✅ [What to do instead]\n"
        )

        return content

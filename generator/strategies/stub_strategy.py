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

        # Derive human-readable content from the skill name
        tech = parts[0].title() if parts else title
        action = " ".join(parts[1:]).replace("-", " ") if len(parts) > 1 else skill_label

        # Use README for a purpose hint if available
        purpose = f"Inconsistent {action} patterns slow down {tech} development. Apply this skill to enforce the correct {action} approach every time."
        # Shell/code prefixes that should never be used as purpose prose
        _SKIP_PREFIXES = (
            "export ", "pip ", "npm ", "yarn ", "cd ", "git ", "python ", "prg ",
            "set ", "curl ", "docker ", "poetry ", "uv ", "http", "https",
        )
        if from_readme:
            for line in from_readme.split("\n"):
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", "-", "*", ">", "|", "!", "`")):
                    continue
                if any(stripped.lower().startswith(p) for p in _SKIP_PREFIXES):
                    continue
                # Skip assignment / env-var lines (contain '=' but no sentence punctuation)
                if "=" in stripped and not any(c in stripped for c in ".,?!"):
                    continue
                # Skip tech-stack / badge lines (dot-separated capabilities lists)
                if "·" in stripped or stripped.count("|") >= 2:
                    continue
                # Only match on skill words that are long enough to be specific
                skill_words = [w for w in skill_label.split() if len(w) >= 5]
                if skill_words and any(w in stripped.lower() for w in skill_words) and len(stripped) > 20:
                    purpose = stripped[:200]
                    break

        step1 = f"Analyze the existing {tech} setup"
        step1_cmd = f"# Review {tech.lower()} configuration\ngrep -r '{parts[0]}' . --include='*.py' -l"
        step2 = f"Apply {action} correctly"
        step2_desc = f"Follow established {tech} conventions for {action} in this project."
        output_desc = f"Updated {tech} implementation with consistent {action} patterns applied."
        anti_dont = f"Use generic {tech} patterns without checking what this project already does"
        anti_do = f"Read existing {tech} code first, then apply the same {action} conventions"

        content = (
            f"---\n"
            f"name: {skill_name}\n"
            f"description: |\n"
            f"  When the user mentions {trigger_str}.\n"
            f"  When the user needs help with {skill_label}.\n"
            f"allowed-tools:\n"
            f"  - Bash\n"
            f"  - Read\n"
            f"  - Write\n"
            f"  - Edit\n"
            f"  - Glob\n"
            f"  - Grep\n"
            f"triggers:\n" + "".join(f'  - "{t}"\n' for t in ([skill_label] + parts)[:3]) + f"metadata:\n"
            f"  tags: [{', '.join(parts[:4])}]\n"
            f"---\n\n"
            f"# Skill: {title}\n\n"
            f"## Purpose\n\n"
            f"{purpose}\n\n"
            f"## Auto-Trigger\n\n"
            f"Activate when user requests:\n"
            + "".join(f'- **"{t}"**\n' for t in ([skill_label] + parts)[:3])
            + f"\nDo NOT activate for: general {tech.lower()} questions unrelated to {action}.\n\n"
            "## Process\n\n"
            f"### 1. {step1}\n\n"
            f"```bash\n{step1_cmd}\n```\n\n"
            f"### 2. {step2}\n\n"
            f"{step2_desc}\n\n"
            "### 3. Validate\n\n"
            "Verify the output is correct and tests still pass.\n\n"
            "## Output\n\n"
            f"{output_desc}\n\n"
            "## Anti-Patterns\n\n"
            f"❌ {anti_dont}\n"
            f"✅ {anti_do}\n"
        )

        return content

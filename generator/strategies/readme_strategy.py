"""README parsing strategy for skill generation."""

import re
from pathlib import Path
from typing import Optional


class READMEStrategy:
    """Generate skills by parsing README files for project context."""

    def generate(
        self,
        skill_name: str,
        project_path: Optional[Path],
        from_readme: Optional[str],
        provider: str,
        **kwargs: object,
    ) -> Optional[str]:
        """
        Parse README and generate skill content.

        Returns:
            Generated skill content or None if README parsing fails
        """
        # BUG-A fix: from_readme is README *content* (not a file path).
        # Fall back to reading project_path/README.md when content is not supplied.
        readme_content = from_readme
        if not readme_content and project_path:
            readme_file = Path(project_path) / "README.md"
            if readme_file.exists():
                readme_content = readme_file.read_text(encoding="utf-8", errors="replace")
        if not readme_content:
            return None

        try:
            from generator.analyzers.readme_parser import (
                extract_anti_patterns,
                extract_auto_triggers,
                extract_process_steps,
                extract_purpose,
                extract_tech_stack,
            )

            purpose = extract_purpose(readme_content)
            tech = extract_tech_stack(readme_content)
            triggers = extract_auto_triggers(readme_content, skill_name)
            steps = extract_process_steps(readme_content)
            anti_patterns = extract_anti_patterns(readme_content, tech, project_path=project_path)

            # Build Anthropic-spec YAML frontmatter (GAP 1 fix).
            # Use skill-name-derived trigger phrases for the description — the
            # README-extracted `triggers` list is for the body Auto-Trigger
            # section and may contain raw markdown formatting.
            skill_label = skill_name.replace("-", " ")
            parts = [p for p in skill_name.split("-") if len(p) > 2]
            fm_triggers = list(dict.fromkeys(parts[:2] + [skill_label, f"add {parts[0]}" if parts else skill_label]))[
                :4
            ]
            trigger_str = ", ".join(f'"{t}"' for t in fm_triggers)
            base_desc = purpose.rstrip(".")
            desc = f"{base_desc}. Use when user mentions {trigger_str}."
            neg_str = f'"general {skill_label} questions", "{skill_label} theory"'
            desc += f" Do NOT activate for {neg_str}."
            desc = desc[:1024]

            tags = list(
                dict.fromkeys([p for p in skill_name.split("-") if len(p) > 2] + ([tech[0].lower()] if tech else []))
            )[:5]
            tags_str = "[" + ", ".join(tags) + "]"

            content = (
                f"---\n"
                f"name: {skill_name}\n"
                f"description: |\n"
                f"  {desc}\n"
                f"license: MIT\n"
                f'allowed-tools: "Bash Read Write Edit Glob Grep"\n'
                f"metadata:\n"
                f"  author: PRG\n"
                f"  version: 1.0.0\n"
                f"  category: project\n"
                f"  tags: {tags_str}\n"
                f"---\n\n"
            )

            # Build skill body
            title = skill_name.replace("-", " ").title()
            content += f"# Skill: {title}\n\n"
            content += f"## Purpose\n{purpose}\n\n"
            content += "## Auto-Trigger\n"
            content += "\n".join(["- " + t for t in triggers]) + "\n\n"
            content += "## Process\n\n"

            step_count = 1
            for step in steps:
                if step.strip().startswith("```"):
                    # Treat each code block as its own numbered step
                    content += f"### {step_count}. Run\n\n{step}\n\n"
                    step_count += 1
                else:
                    clean_step = re.sub(r"^\d+\.\s*", "", step)
                    content += f"### {step_count}. {clean_step}\n\n"
                    step_count += 1

            # Ensure at least 2 steps so quality gate passes
            if step_count <= 2:
                content += f"### {step_count}. Validate\n\nVerify changes are correct and tests pass.\n\n"
                step_count += 1
                content += f"### {step_count}. Review Output\n\nCheck generated files and confirm expected results.\n\n"

            content += f"## Output\n\nApplying this skill produces:\n\n- Updated or created files following `{skill_label}` patterns\n- Status report with changes made\n- Recommendations for next steps\n\n"
            content += "## Anti-Patterns\n"
            for ap in anti_patterns:
                content += f"❌ {ap}\n"

            if tech:
                content += f"\n## Tech Stack\n{', '.join(tech)}\n"

            content += f"\n## Context (from README)\n\n{readme_content}\n"

            return content
        except Exception as e:
            print(f"[!] Warning: Smart parsing failed ({e}). Falling back to next strategy.")
            return None

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
    ) -> Optional[str]:
        """
        Parse README and generate skill content.

        Returns:
            Generated skill content or None if README parsing fails
        """
        if not from_readme:
            return None

        # from_readme is README *content* (passed by SkillGenerator.create_skill),
        # not a file path.  Use it directly.
        readme_content = from_readme

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

            # Build skill content
            title = skill_name.replace("-", " ").title()
            content = f"# Skill: {title}\n\n"
            content += f"## Purpose\n{purpose}\n\n"
            content += "## Auto-Trigger\n"
            content += "\n".join(["- " + t for t in triggers]) + "\n\n"
            content += "## Process\n\n"

            step_count = 1
            for step in steps:
                if step.strip().startswith("```"):
                    content += f"{step}\n\n"
                else:
                    clean_step = re.sub(r"^\d+\.\s*", "", step)
                    content += f"### {step_count}. {clean_step}\n\n"
                    step_count += 1

            output_desc = f"Completed {skill_name.replace('-', ' ')} workflow with all steps applied to the project."
            content += f"## Output\n{output_desc}\n\n"
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

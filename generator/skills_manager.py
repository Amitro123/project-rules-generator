from pathlib import Path
from typing import List, Dict, Optional
import re

class SkillsManager:
    """Manages skill discovery, creation, and loading."""

    def __init__(self, base_path: Optional[Path] = None):
        # Default to skills/ directory relative to this file (in generator package)
        if base_path is None:
            self.base_path = Path(__file__).parent / "skills"
        else:
            self.base_path = base_path
            
        self.builtin_path = self.base_path / "builtin"
        self.awesome_path = self.base_path / "awesome"
        
        # storage for learned skills (user directory)
        self.learned_path = Path.home() / ".project-rules-generator" / "learned_skills"

    def list_skills(self) -> Dict[str, List[str]]:
        """List all available skills organized by category."""
        skills = {
            "builtin": [],
            "awesome": [],
            "learned": []
        }

        for category, path in [("builtin", self.builtin_path), ("awesome", self.awesome_path), ("learned", self.learned_path)]:
            if path.exists():
                skills[category] = sorted(self._scan_directory(path))

        return skills

    def _scan_directory(self, path: Path, prefix: str = "") -> List[str]:
        """Recursively scan for skills (directories containing SKILL.md)."""
        found = []
        try:
            for item in path.iterdir():
                if item.is_dir():
                    if (item / "SKILL.md").exists():
                        found.append(f"{prefix}{item.name}")
                    # Recurse for nested categories/skills
                    # Note: If a directory is a skill (has SKILL.md), we might still want to check inside?
                    # But usually a skill is a leaf.
                    # The 'meta/writing-skills' case implies 'meta' is a container folder, not a skill itself?
                    # Or 'meta' could be a skill with sub-skills?
                    # Assuming standard directory traversal.
                    found.extend(self._scan_directory(item, prefix=f"{prefix}{item.name}/"))
        except PermissionError:
            pass
        return found

    def create_skill(self, name: str, from_readme: Optional[str] = None) -> Path:
        """Create a new learned skill."""
        # Sanitize name
        safe_name = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
        if not safe_name:
            raise ValueError("Invalid skill name provided.")

        target_dir = self.learned_path / safe_name
        if target_dir.exists():
            raise FileExistsError(f"Skill '{safe_name}' already exists.")

        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        content = ""
        if from_readme:
            readme_path = Path(from_readme)
            if readme_path.exists():
                try:
                    from analyzer.readme_parser import (
                        extract_purpose, extract_tech_stack, 
                        extract_auto_triggers, extract_process_steps, 
                        extract_anti_patterns
                    )
                    
                    readme_content = readme_path.read_text(encoding='utf-8', errors='replace')
                    
                    purpose = extract_purpose(readme_content)
                    tech = extract_tech_stack(readme_content)
                    triggers = extract_auto_triggers(readme_content, safe_name)
                    steps = extract_process_steps(readme_content)
                    anti_patterns = extract_anti_patterns(readme_content, tech)
                    
                    # Build skill content
                    title = safe_name.replace('-', ' ').title()
                    content = f"# Skill: {title}\n\n"
                    content += f"## Purpose\n{purpose}\n\n"
                    
                    content += "## Auto-Trigger\n"
                    content += "\n".join(['- ' + t for t in triggers]) + "\n\n"
                    
                    content += "## Process\n\n"
                    step_count = 1
                    for step in steps:
                        if step.strip().startswith('```'):
                            content += f"{step}\n\n"
                        else:
                            # Clean existing numbering
                            clean_step = re.sub(r'^\d+\.\s*', '', step)
                            content += f"### {step_count}. {clean_step}\n\n"
                            step_count += 1
                            
                    content += "## Output\n[Describe what artifacts or state changes result from following this skill]\n\n"
                    
                    content += "## Anti-Patterns\n"
                    for ap in anti_patterns:
                        content += f"❌ {ap}\n"
                        
                    if tech:
                        content += f"\n## Tech Stack\n{', '.join(tech)}\n"
                        
                    content += f"\n## Context (from {readme_path.name})\n\n{readme_content}\n"

                except Exception as e:
                    print(f"[!] Warning: Smart parsing failed ({e}). Falling back to template.")
                    # Fallthrough to template + context
                    pass
            else:
                 print(f"[!] Warning: README {from_readme} not found.")

        # Fallback / Default Template if content not generated
        if not content:
            if from_readme and Path(from_readme).exists():
                 # Valid readme but parsing failed or was skipped
                 readme_path = Path(from_readme)
                 readme_content = readme_path.read_text(encoding='utf-8', errors='replace')
                 additional_context = f"\n\n## Context (from {readme_path.name})\n\n{readme_content}\n"
            else:
                 additional_context = ""

            title = safe_name.replace('-', ' ').title()
            content = f"""# Skill: {title}

## Purpose
[One sentence: what problem does this solve]

## Auto-Trigger
[When should agent activate this skill]

## Process
[Step-by-step instructions]

## Output
[What artifact/state results]

## Anti-Patterns
[x] [What NOT to do]
"""
            content += additional_context

        skill_file.write_text(content, encoding='utf-8')
        return target_dir

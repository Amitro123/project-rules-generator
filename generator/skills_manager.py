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
        self.learned_path = self.base_path / "learned"

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
        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', name)
        if not clean_name:
            raise ValueError("Invalid skill name provided.")

        target_dir = self.learned_path / clean_name
        if target_dir.exists():
            raise FileExistsError(f"Skill '{clean_name}' already exists.")

        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        # Default Template
        title = clean_name.replace('-', ' ').title()
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

        if from_readme:
            readme_path = Path(from_readme)
            if readme_path.exists():
                readme_content = readme_path.read_text(encoding='utf-8', errors='replace')
                content += f"\n\n## Context (from {readme_path.name})\n\n{readme_content}\n"
            else:
                 # We raise here so the caller can warn the user, or we can just log/print.
                 # For now, let's include a warning in the file itself/log.
                 # Raising might abort creation, which is maybe not desired if just the context is missing.
                 # But keeping consistent with previous logic:
                 print(f"[!] Warning: README {from_readme} not found.")

        skill_file.write_text(content, encoding='utf-8')
        return target_dir

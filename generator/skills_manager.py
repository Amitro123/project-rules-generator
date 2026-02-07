from pathlib import Path
from typing import List, Dict, Optional
import re

class SkillsManager:
    """Manages skill discovery, creation, and loading."""

    def __init__(self, base_path: Path = Path("skills")):
        self.base_path = base_path
        self.builtin_path = base_path / "builtin"
        self.awesome_path = base_path / "awesome"
        self.learned_path = base_path / "learned"

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

        content = f"# {clean_name.replace('-', ' ').title()}\n\n## Purpose\n(Describe the purpose)\n\n## Auto-Trigger\n(When should this run?)\n\n## Process\n1. Step 1\n2. Step 2\n\n## Anti-Patterns\n- Mistake 1\n"

        if from_readme:
            readme_path = Path(from_readme)
            if readme_path.exists():
                readme_content = readme_path.read_text(encoding='utf-8', errors='replace')
                # Simplistic inclusion
                content = f"{content}\n## Context from README\n<!--\n{readme_content}\n-->\n"
            else:
                # Warn or just ignore? The CLI should handle the error probably.
                # Here we just note it.
                content += f"\n## Context\n(README {from_readme} not found)\n"

        (target_dir / "SKILL.md").write_text(content, encoding='utf-8')
        return target_dir

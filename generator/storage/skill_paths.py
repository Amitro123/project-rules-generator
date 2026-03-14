"""Manage builtin and learned skill locations."""

import logging
import shutil
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SkillPathManager:
    """Manage builtin and learned skill locations with sync support.

    Path constants mirror ``SkillDiscovery.global_*`` — they must stay in sync.
    Single source of truth for the base directory is ``GLOBAL_DIR``.
    """

    # Builtin source (in project repo)
    BUILTIN_SOURCE = Path(__file__).parent.parent / "skills" / "builtin"

    # Global user directory — MUST match SkillDiscovery.global_root
    GLOBAL_DIR = Path.home() / ".project-rules-generator"
    GLOBAL_BUILTIN = GLOBAL_DIR / "builtin"
    GLOBAL_LEARNED = GLOBAL_DIR / "learned"

    @classmethod
    def ensure_setup(cls):
        """Create directories and sync builtin skills."""
        cls.GLOBAL_DIR.mkdir(exist_ok=True)
        cls.GLOBAL_BUILTIN.mkdir(exist_ok=True)
        cls.GLOBAL_LEARNED.mkdir(exist_ok=True)

        cls.sync_builtin_skills()

    @classmethod
    def sync_builtin_skills(cls):
        """Copy builtin skills from project to global if newer."""
        if not cls.BUILTIN_SOURCE.exists():
            logger.debug(f"Builtin source not found: {cls.BUILTIN_SOURCE}")
            return

        synced_count = 0
        for skill_item in cls.BUILTIN_SOURCE.iterdir():
            if skill_item.is_file() and skill_item.suffix in (".md", ".yaml", ".yml"):
                target = cls.GLOBAL_BUILTIN / skill_item.name
                if not target.exists() or skill_item.stat().st_mtime > target.stat().st_mtime:
                    shutil.copy2(skill_item, target)
                    synced_count += 1
                    logger.info(f"Synced builtin: {skill_item.name}")

            elif skill_item.is_dir():
                # Sync entire skill directory (e.g., builtin/code-review/)
                target_dir = cls.GLOBAL_BUILTIN / skill_item.name
                target_dir.mkdir(exist_ok=True)

                for sub_file in skill_item.rglob("*"):
                    if sub_file.is_file():
                        rel = sub_file.relative_to(skill_item)
                        target_file = target_dir / rel
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        if not target_file.exists() or sub_file.stat().st_mtime > target_file.stat().st_mtime:
                            shutil.copy2(sub_file, target_file)
                            synced_count += 1

        if synced_count > 0:
            logger.info(f"Synced {synced_count} builtin skill files to {cls.GLOBAL_BUILTIN}")

    @classmethod
    def save_learned_skill(cls, skill: Dict, category: str) -> Path:
        """
        Save learned skill to global directory.

        Args:
            skill: {'name': 'async-patterns', 'content': '...'}
            category: 'fastapi', 'python-cli', etc.

        Returns:
            Path to saved skill file
        """
        cls.ensure_setup()

        category_dir = cls.GLOBAL_LEARNED / category
        category_dir.mkdir(parents=True, exist_ok=True)

        skill_name = skill.get("name", "unnamed-skill")
        skill_content = skill.get("content", "")

        # Determine file extension based on content
        if skill_content.strip().startswith("---") or skill_content.strip().startswith("name:"):
            ext = ".yaml"
        else:
            ext = ".md"

        skill_path = category_dir / f"{skill_name}{ext}"
        skill_path.write_text(skill_content, encoding="utf-8")

        logger.info(f"Saved learned skill: {skill_path}")
        return skill_path

    @classmethod
    def get_learned_skill(cls, category: str, name: str) -> Optional[str]:
        """Load a learned skill's content."""
        for ext in (".md", ".yaml", ".yml"):
            path = cls.GLOBAL_LEARNED / category / f"{name}{ext}"
            if path.exists():
                return path.read_text(encoding="utf-8", errors="replace")
        return None

    @classmethod
    def list_learned_skills(cls) -> Dict[str, list]:
        """List all learned skills organized by category."""
        result: Dict[str, list] = {}
        if not cls.GLOBAL_LEARNED.exists():
            return result

        for category_dir in cls.GLOBAL_LEARNED.iterdir():
            if category_dir.is_dir():
                skills = []
                for f in category_dir.iterdir():
                    if f.is_file() and f.suffix in (".md", ".yaml", ".yml"):
                        skills.append(f.stem)
                    elif f.is_dir() and (f / "SKILL.md").exists():
                        skills.append(f.name)
                if skills:
                    result[category_dir.name] = sorted(skills)

        return result

    @classmethod
    def list_builtin_skills(cls) -> list:
        """List all builtin skills."""
        skills: list = []
        if not cls.GLOBAL_BUILTIN.exists():
            return skills

        for item in cls.GLOBAL_BUILTIN.iterdir():
            if item.is_file() and item.suffix in (".md", ".yaml", ".yml"):
                skills.append(item.stem)
            elif item.is_dir() and (item / "SKILL.md").exists():
                skills.append(item.name)

        return sorted(skills)

    @classmethod
    def get_skill_path(cls, skill_ref: str) -> Optional[Path]:
        """
        Resolve a skill reference to its actual file path.

        Args:
            skill_ref: 'builtin/code-review' or 'learned/fastapi/async-patterns'

        Returns:
            Path to the skill file, or None if not found
        """
        parts = skill_ref.split("/")

        if len(parts) < 2:
            return None

        source_type = parts[0]

        if source_type == "builtin":
            name = parts[-1]
            base = cls.GLOBAL_BUILTIN
            # Check various extensions and structures
            for ext in (".md", ".yaml", ".yml"):
                path = base / f"{name}{ext}"
                if path.exists():
                    return path
            # Check directory style
            dir_path = base / name / "SKILL.md"
            if dir_path.exists():
                return dir_path

        elif source_type == "learned":
            if len(parts) >= 3:
                category = parts[1]
                name = parts[2]
            else:
                category = ""
                name = parts[1]

            base = cls.GLOBAL_LEARNED
            if category:
                for ext in (".md", ".yaml", ".yml"):
                    path = base / category / f"{name}{ext}"
                    if path.exists():
                        return path
            else:
                # Search all categories
                for cat_dir in base.iterdir():
                    if cat_dir.is_dir():
                        for ext in (".md", ".yaml", ".yml"):
                            path = cat_dir / f"{name}{ext}"
                            if path.exists():
                                return path

        return None

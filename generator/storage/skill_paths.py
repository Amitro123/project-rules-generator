"""Manage builtin and learned skill locations."""

import logging
import shutil
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SkillPathManager:
    """Manage builtin and learned skill locations with sync support.

    Single source of truth for all global skill paths.
    ``SkillDiscovery`` reads its global paths from these constants — do not
    duplicate them anywhere else.
    """

    # Builtin source (in project repo)
    BUILTIN_SOURCE = Path(__file__).parent.parent / "skills" / "builtin"

    # Global user directory — SkillDiscovery.global_root reads FROM here (single source of truth)
    GLOBAL_DIR = Path.home() / ".project-rules-generator"
    GLOBAL_BUILTIN = GLOBAL_DIR / "builtin"
    GLOBAL_LEARNED = GLOBAL_DIR / "learned"

    @classmethod
    def ensure_setup(cls):
        """Create directories and sync builtin skills."""
        cls.GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
        cls.GLOBAL_BUILTIN.mkdir(parents=True, exist_ok=True)
        cls.GLOBAL_LEARNED.mkdir(parents=True, exist_ok=True)

        cls.sync_builtin_skills()

    @classmethod
    def sync_builtin_skills(cls):
        """Copy builtin skills from project to global if newer."""
        if not cls.BUILTIN_SOURCE.exists():
            logger.debug("Builtin source not found: %s", cls.BUILTIN_SOURCE)
            return

        synced_count = 0
        for skill_item in cls.BUILTIN_SOURCE.iterdir():
            if skill_item.is_file() and skill_item.suffix in (".md", ".yaml", ".yml"):
                target = cls.GLOBAL_BUILTIN / skill_item.name
                if not target.exists() or skill_item.stat().st_mtime > target.stat().st_mtime:
                    shutil.copy2(skill_item, target)
                    synced_count += 1
                    logger.info("Synced builtin: %s", skill_item.name)

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
            logger.info("Synced %d builtin skill files to %s", synced_count, cls.GLOBAL_BUILTIN)

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

        # Always write in the standard subfolder/SKILL.md layout
        skill_dir = category_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"

        if not cls._within_base(skill_path, cls.GLOBAL_LEARNED):
            raise ValueError(f"Skill path {skill_path} escapes learned skills directory")

        skill_path.write_text(skill_content, encoding="utf-8")

        logger.info("Saved learned skill: %s", skill_path)
        return skill_path

    @staticmethod
    def _within_base(candidate: Path, base: Path) -> bool:
        """Return True only if candidate resolves to a path inside base."""
        try:
            candidate.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

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

        # Reject any part that could escape the base directory
        if any(".." in p or "\\" in p for p in parts):
            return None

        source_type = parts[0]

        if source_type == "builtin":
            name = parts[-1]
            base = cls.GLOBAL_BUILTIN
            # Prefer subfolder layout (name/SKILL.md) — matches the canonical export format
            dir_path = base / name / "SKILL.md"
            if cls._within_base(dir_path, base) and dir_path.exists():
                return dir_path
            # Fallback: flat file layout (legacy)
            for ext in (".md", ".yaml", ".yml"):
                path = base / f"{name}{ext}"
                if cls._within_base(path, base) and path.exists():
                    return path

        elif source_type == "learned":
            if len(parts) >= 3:
                category = parts[1]
                name = parts[2]
            else:
                category = ""
                name = parts[1]

            base = cls.GLOBAL_LEARNED
            if category:
                # Prefer subfolder layout (category/name/SKILL.md) — matches save_learned_skill output
                subfolder = base / category / name / "SKILL.md"
                if cls._within_base(subfolder, base) and subfolder.exists():
                    return subfolder
                # Fallback: flat file layout (category/name.md)
                for ext in (".md", ".yaml", ".yml"):
                    path = base / category / f"{name}{ext}"
                    if cls._within_base(path, base) and path.exists():
                        return path
            else:
                # Search all categories
                for cat_dir in base.iterdir():
                    if cat_dir.is_dir():
                        # Prefer subfolder layout first
                        subfolder = cat_dir / name / "SKILL.md"
                        if cls._within_base(subfolder, base) and subfolder.exists():
                            return subfolder
                        for ext in (".md", ".yaml", ".yml"):
                            path = cat_dir / f"{name}{ext}"
                            if cls._within_base(path, base) and path.exists():
                                return path

        return None

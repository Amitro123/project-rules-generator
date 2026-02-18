import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillDiscovery:
    """Manages skill discovery, paths, and structure."""

    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize with Global and Project layers.

        Layers:
        1. Project (.clinerules/skills/project) - Metric overrides
        2. Global Learned (~/.project-rules-generator/learned) - User's shared skills
        3. Global Builtin (~/.project-rules-generator/builtin) - Core PRG skills
        """
        self.project_path = Path(project_path) if project_path else None

        # 1. Global Cache Paths
        self.global_root = Path.home() / ".project-rules-generator"
        self.global_builtin = self.global_root / "builtin"
        self.global_learned = self.global_root / "learned"

        # 2. Package Source (for syncing builtin)
        # Note: This assumes this file is in generator/ (sibling to skills_manager)
        # parent = generator/
        # parent.parent = project root
        # But wait, original code was in generator/skills_manager.py: Path(__file__).parent / "skills" / "builtin"
        # If I put this in generator/skill_discovery.py, same relative path applies.
        self.package_builtin = Path(__file__).parent / "skills" / "builtin"

        # 3. Project Paths (if valid project)
        if self.project_path:
            self.project_skills_root = self.project_path / ".clinerules" / "skills"
            self.project_local_dir = self.project_skills_root / "project"
            self.project_learned_link = self.project_skills_root / "learned"
            self.project_builtin_link = self.project_skills_root / "builtin"
        else:
            self.project_skills_root = None
            self.project_local_dir = None
            self.project_learned_link = None
            self.project_builtin_link = None

    def ensure_global_structure(self):
        """Ensure global cache directories exist and are synced."""
        self.global_root.mkdir(parents=True, exist_ok=True)
        self.global_learned.mkdir(parents=True, exist_ok=True)
        self.global_builtin.mkdir(parents=True, exist_ok=True)

        # Sync package builtin skills to global cache
        if self.package_builtin.exists():
            try:
                for item in self.package_builtin.iterdir():
                    dest = self.global_builtin / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
            except Exception as e:
                print(f"[Warning] Failed to sync builtin skills to global cache: {e}")

    def setup_project_structure(self):
        """
        Create project .clinerules/skills structure with symlinks to global cache.
        """
        if not self.project_skills_root:
            raise ValueError("Project path not set")

        self.ensure_global_structure()

        # 1. Create local overrides dir
        self.project_local_dir.mkdir(parents=True, exist_ok=True)

        # 2. Link/Copy Builtin & Learned
        self._link_or_copy(self.global_builtin, self.project_builtin_link)
        self._link_or_copy(self.global_learned, self.project_learned_link)

    def _link_or_copy(self, source: Path, target: Path):
        """Try to symlink, fallback to copy."""
        if target.exists():
            if target.is_symlink():
                try:
                    if target.resolve() != source.resolve():
                        target.unlink()
                    else:
                        return  # Already correct
                except Exception:
                    target.unlink()
            elif target.is_dir():
                # Directory exists (maybe copy), leave it be
                return

        # Try symlink
        try:
            os.symlink(source, target, target_is_directory=True)
        except (OSError, AttributeError):
            # Fallback to copy
            if source.exists():
                try:
                    if source.is_dir():
                        shutil.copytree(source, target)
                except Exception as copy_err:
                    print(
                        f"[Warning] Failed to link or copy {source} to {target}: {copy_err}"
                    )

    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available skills with their source resolution.
        Returns: { 'skill_name': {'type': 'builtin'|'learned'|'project', 'path': ...} }
        """
        self.ensure_global_structure()

        skills = {}

        def _resolve_path(base: Path, name: str) -> Optional[Path]:
            # Check for file
            p_md = base / f"{name}.md"
            if p_md.exists(): return p_md
            
            p_yaml = base / f"{name}.yaml"
            if p_yaml.exists(): return p_yaml
            
            p_yml = base / f"{name}.yml"
            if p_yml.exists(): return p_yml

            # Check for directory
            p_dir = base / name / "SKILL.md"
            if p_dir.exists(): return p_dir
            
            # Handle subdirectories in name (e.g. learned/foo)
            # The 'name' from _scan_directory might include slashes
            p_direct = base / f"{name}.md" 
            if p_direct.exists(): return p_direct

            return None

        # 1. Load Builtin (Lowest Priority)
        for s in self._scan_directory(self.global_builtin):
            name = s.split("/")[-1]
            path = _resolve_path(self.global_builtin, s)
            if path:
                skills[name] = {"type": "builtin", "path": path}

        # 2. Load Learned (Medium Priority)
        for s in self._scan_directory(self.global_learned):
            name = s.split("/")[-1]
            path = _resolve_path(self.global_learned, s)
            if path:
                skills[name] = {"type": "learned", "path": path}

        # 3. Load Project (Highest Priority)
        if self.project_local_dir and self.project_local_dir.exists():
            for s in self._scan_directory(self.project_local_dir):
                name = s.split("/")[-1]
                path = _resolve_path(self.project_local_dir, s)
                if path:
                    skills[name] = {
                        "type": "project",
                        "path": path,
                    }

        return skills

    def resolve_skill(self, skill_name: str) -> Optional[Path]:
        """Find the active skill file based on priority."""
        # Check Project
        if self.project_local_dir:
            p_path = self.project_local_dir / f"{skill_name}.md"
            if p_path.exists():
                return p_path

        # Check Learned
        l_path = self.global_learned / f"{skill_name}.md"
        if l_path.exists():
            return l_path

        l_subdir = self.global_learned / skill_name / "SKILL.md"
        if l_subdir.exists():
            return l_subdir

        # Check Builtin
        b_path = self.global_builtin / f"{skill_name}.md"
        if b_path.exists():
            return b_path

        # Deep search
        for root in [self.global_learned, self.global_builtin]:
            found = list(root.rglob(f"{skill_name}.md"))
            if found:
                return found[0]
            found_dir = list(root.rglob(f"{skill_name}/SKILL.md"))
            if found_dir:
                return found_dir[0]

        return None

    def skill_exists(self, skill_name: str, scope: str = "learned") -> bool:
        """Check if a skill already exists, preventing duplicates.

        Checks all storage formats:
        - Flat file:   <scope>/<skill_name>.md
        - Directory:   <scope>/<skill_name>/SKILL.md

        Args:
            skill_name: Normalized skill name (lowercase, hyphens)
            scope: 'learned' (default), 'builtin', or 'project'

        Returns:
            True if the skill exists in any format in the given scope.
        """
        if scope == "learned":
            base = self.global_learned
        elif scope == "builtin":
            base = self.global_builtin
        elif scope == "project":
            base = self.project_local_dir
        else:
            raise ValueError(f"Unknown scope: {scope!r}. Use 'learned', 'builtin', or 'project'.")

        if not base or not base.exists():
            return False

        # Check flat file
        if (base / f"{skill_name}.md").exists():
            return True
        # Check directory format
        if (base / skill_name / "SKILL.md").exists():
            return True
        return False

    def _scan_directory(self, path: Path, prefix: str = "") -> List[str]:
        """Recursively scan for skills (YAML or SKILL.md)."""
        found = []
        if not path.exists():
            return found

        try:
            for item in path.iterdir():
                if item.is_file() and item.suffix in [".yaml", ".yml", ".md"]:
                    found.append(f"{prefix}{item.stem}")
                elif item.is_dir():
                    if (item / "SKILL.md").exists():
                        found.append(f"{prefix}{item.name}")
                    else:
                        found.extend(
                            self._scan_directory(item, prefix=f"{prefix}{item.name}/")
                        )
        except PermissionError:
            pass
        return found

    def get_all_skills_content(self) -> Dict[str, Dict]:
        """Get full content of all skills for export (Project > Learned > Builtin)."""
        self.ensure_global_structure()

        skills_content = {"project": {}, "learned": {}, "builtin": {}}

        def _read_skills_from_path(path: Path, category: str):
            if not path or not path.exists():
                return
            skills_list = self._scan_directory(path)
            for skill_rel_path in skills_list:
                md_path = path / f"{skill_rel_path}.md"
                dir_md_path = path / skill_rel_path / "SKILL.md"
                yaml_path = path / f"{skill_rel_path}.yaml"

                skill_file = None
                if md_path.exists():
                    skill_file = md_path
                elif dir_md_path.exists():
                    skill_file = dir_md_path
                elif yaml_path.exists():
                    skill_file = yaml_path

                if skill_file:
                    content = skill_file.read_text(encoding="utf-8", errors="replace")
                    skill_name = skill_rel_path.split("/")[-1]
                    skills_content[category][skill_name] = {
                        "path": str(skill_file),
                        "content": content,
                    }

        _read_skills_from_path(self.global_builtin, "builtin")
        _read_skills_from_path(self.global_learned, "learned")
        if self.project_local_dir:
            _read_skills_from_path(self.project_local_dir, "project")

        return skills_content

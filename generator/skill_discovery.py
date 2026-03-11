import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillDiscovery:
    """Manages skill discovery, paths, and structure."""

    def __init__(self, project_path: Optional[Path] = None, skills_dir: Optional[Path] = None):
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
        # Declare as Optional so both if/else branches are consistent
        self.project_skills_root: Optional[Path] = None
        self.project_local_dir: Optional[Path] = None
        self.project_learned_link: Optional[Path] = None
        self.project_builtin_link: Optional[Path] = None

        if self.project_path:
            # Allow override or default to new standard (.clinerules/skills)
            if skills_dir:
                # User provided skills_dir (e.g. from CLI)
                proposed_root = Path(skills_dir)
                if not proposed_root.is_absolute():
                    self.project_skills_root = self.project_path / proposed_root
                else:
                    self.project_skills_root = proposed_root
            else:
                # Default: .clinerules/skills
                self.project_skills_root = self.project_path / ".clinerules" / "skills"

            # Point directly to the standard locations used by migration
            self.project_local_dir = self.project_skills_root / "project"
            self.project_learned_link = self.project_skills_root / "learned"
            self.project_builtin_link = self.project_skills_root / "builtin"

        self._skills_cache: Optional[Dict[str, Any]] = None

    def _build_cache(self):
        """Build a unified cache of all available skills across all layers."""
        self.ensure_global_structure()

        self._skills_cache = {"project": {}, "learned": {}, "builtin": {}}
        if hasattr(self, "_layer_skills_cache"):
            del self._layer_skills_cache

        def _scan(root: Path):
            if not root or not root.exists():
                return {"by_rel": {}, "by_name": {}}

            idx: Dict[str, Dict[str, Path]] = {
                "by_rel": {},  # "math/add.md" -> Path (always forward slashes)
                "by_name": {},  # "add.md" -> Path (first found)
            }
            try:
                # Use a single pass over the directory tree
                for p in root.rglob("*"):
                    if p.is_file() and p.suffix in [".md", ".yaml", ".yml"]:
                        # Normalize to forward slashes for cross-platform consistency
                        rel = p.relative_to(root).as_posix()
                        idx["by_rel"][rel] = p
                        if p.name not in idx["by_name"]:
                            idx["by_name"][p.name] = p
            except (PermissionError, OSError):
                pass
            return idx

        self._skills_cache["builtin"] = _scan(self.global_builtin)
        self._skills_cache["learned"] = _scan(self.global_learned)
        if self.project_local_dir:
            self._skills_cache["project"] = _scan(self.project_local_dir)

    def invalidate_cache(self) -> None:
        """Reset the skills cache so the next lookup rebuilds it from disk.

        Call this after creating or deleting skills to prevent stale-data bugs
        where list_skills() / resolve_skill() return outdated results.
        """
        self._skills_cache = None
        if hasattr(self, "_layer_skills_cache"):
            del self._layer_skills_cache

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
                logger.warning("Failed to sync builtin skills to global cache: %s", e)

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
            os.symlink(source, target, target_is_directory=source.is_dir())
        except (OSError, AttributeError):
            # Fallback to copy (common on Windows without elevated symlink privilege)
            if source.exists():
                try:
                    if source.is_dir():
                        shutil.copytree(source, target)
                    else:
                        shutil.copy2(source, target)
                except Exception as copy_err:
                    logger.warning("Failed to link or copy %s to %s: %s", source, target, copy_err)

    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available skills with their source resolution.
        Returns: { 'skill_name': {'type': 'builtin'|'learned'|'project', 'path': ...} }
        """
        if self._skills_cache is None:
            self._build_cache()

        skills = {}

        # 1. Load Builtin (Lowest Priority)
        builtin_skills = self._get_layer_skills("builtin")
        for name, path in builtin_skills.items():
            skills[name] = {"type": "builtin", "path": path}

        # 2. Load Learned (Medium Priority)
        learned_skills = self._get_layer_skills("learned")
        for name, path in learned_skills.items():
            skills[name] = {"type": "learned", "path": path}

        # 3. Load Project (Highest Priority)
        project_skills = self._get_layer_skills("project")
        for name, path in project_skills.items():
            skills[name] = {"type": "project", "path": path}

        return skills

    def _get_layer_skills(self, layer: str) -> Dict[str, Path]:
        """Get all skills in a layer, respecting the stop-at-SKILL.md logic."""
        if self._skills_cache is None:
            self._build_cache()
        assert self._skills_cache is not None

        if not hasattr(self, "_layer_skills_cache"):
            self._layer_skills_cache: Dict[str, Dict[str, Path]] = {}

        if layer in self._layer_skills_cache:
            return self._layer_skills_cache[layer]

        root = {
            "builtin": self.global_builtin,
            "learned": (
                self.project_learned_link
                if self.project_learned_link and self.project_learned_link.exists()
                else self.global_learned
            ),
            "project": self.project_local_dir,
        }.get(layer)

        if not root or not root.exists():
            return {}

        idx = self._skills_cache[layer]
        skills: Dict[str, Path] = {}
        skills_prio: Dict[str, int] = {}
        # Priority matching _resolve_path: .md > .yaml > .yml > SKILL.md
        priority = {".md": 4, ".yaml": 3, ".yml": 2, "SKILL.md": 1}

        # Replicate _scan_directory's stop-at-SKILL.md recursive logic
        rel_paths = sorted(idx["by_rel"].keys())
        skill_dirs = set()
        for rel in rel_paths:
            if rel == "SKILL.md" or rel.endswith("/SKILL.md"):
                sd = "" if rel == "SKILL.md" else rel[:-9]
                skill_dirs.add(sd)

        for rel in rel_paths:
            path = idx["by_rel"][rel]

            # Check if this path is inside a skill directory (and not the SKILL.md itself)
            is_inside_skill_dir = False
            for sd in skill_dirs:
                if sd == "":
                    continue  # SKILL.md in root doesn't hide anything
                if rel.startswith(f"{sd}/") and rel != f"{sd}/SKILL.md":
                    is_inside_skill_dir = True
                    break
            if is_inside_skill_dir:
                continue

            # Skill name logic matches split("/")[-1] from list_skills
            if rel == "SKILL.md" or rel.endswith("/SKILL.md"):
                name = rel[:-9].split("/")[-1] if "/" in rel else rel.rsplit(".", 1)[0]
                prio = 1
            else:
                name = rel.rsplit(".", 1)[0].split("/")[-1]
                prio = priority.get(path.suffix, 0)

            # Use priority to decide which one wins for the same base name
            if name not in skills or prio > skills_prio.get(name, 0):
                skills[name] = path
                skills_prio[name] = prio

        self._layer_skills_cache[layer] = skills
        return skills

    def resolve_skill(self, skill_name: str) -> Optional[Path]:
        """Find the active skill file based on priority."""
        if self._skills_cache is None:
            self._build_cache()
        assert self._skills_cache is not None

        # 1. Check Project
        if self.project_local_dir:
            p_path = self._skills_cache["project"]["by_rel"].get(f"{skill_name}.md")
            if p_path:
                return p_path
            # BUG-4 fix: also check directory-style in project layer
            p_dir = self._skills_cache["project"]["by_rel"].get(f"{skill_name}/SKILL.md")
            if p_dir:
                return p_dir

        # 2. Check Learned
        l_path = self._skills_cache["learned"]["by_rel"].get(f"{skill_name}.md")
        if l_path:
            return l_path

        l_subdir = self._skills_cache["learned"]["by_rel"].get(f"{skill_name}/SKILL.md")
        if l_subdir:
            return l_subdir

        # 3. Check Builtin
        b_path = self._skills_cache["builtin"]["by_rel"].get(f"{skill_name}.md")
        if b_path:
            return b_path

        # 4. Deep search
        for layer in ["learned", "builtin"]:
            idx = self._skills_cache[layer]

            # Match rglob(f"{skill_name}.md")
            target_file = f"{skill_name}.md"
            if "/" not in skill_name:
                found = idx["by_name"].get(target_file)
                if found:
                    return found
            else:
                for rel, path in idx["by_rel"].items():
                    if rel == target_file or rel.endswith(f"/{target_file}"):
                        return path

            # Match rglob(f"{skill_name}/SKILL.md")
            target_dir_skill = f"{skill_name}/SKILL.md"
            for rel, path in idx["by_rel"].items():
                if rel == target_dir_skill or rel.endswith(f"/{target_dir_skill}"):
                    return path

        return None

    def resolve_active_skills(self, query: str) -> List[Path]:
        """Return ALL skills whose triggers match the query (composable, GAP 7).

        Unlike resolve_skill() which returns one skill by name, this checks
        every known skill's embedded trigger phrases against the query and
        returns all that match — enabling multi-skill composition per the
        Anthropic spec.

        Scans all layers in priority order (project > learned > builtin).
        Project-layer skill overrides a same-named builtin/learned one.

        Args:
            query: User query string to match against skill triggers

        Returns:
            List of paths to matching SKILL.md files (deduplicated by skill name)
        """
        from generator.utils.trigger_evaluator import TriggerEvaluator

        # Collect all SKILL.md and *.md files across all layers
        # Higher-priority layers win by name deduplication
        skill_roots: List[Optional[Path]] = [
            self.project_local_dir,  # highest priority
            self.project_learned_link if self.project_learned_link else None,
            self.global_learned,
            self.global_builtin,
        ]

        seen_names: set = set()
        active: List[Path] = []

        for root in skill_roots:
            if not root or not root.exists():
                continue
            # Collect all candidate skill files in this root
            candidates: List[Path] = list(root.rglob("SKILL.md")) + [
                p for p in root.rglob("*.md") if p.name != "SKILL.md"
            ]
            for skill_path in candidates:
                # Use parent-dir name (for SKILL.md) or stem (for flat .md) as skill name
                skill_name = skill_path.parent.name if skill_path.name == "SKILL.md" else skill_path.stem
                if skill_name in seen_names:
                    continue
                seen_names.add(skill_name)
                try:
                    content = skill_path.read_text(encoding="utf-8", errors="replace")
                    triggers = TriggerEvaluator.extract_triggers(content)
                    if triggers and TriggerEvaluator._matches_any(query, triggers):
                        active.append(skill_path)
                except Exception:
                    continue

        return active

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
        base: Optional[Path]
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

        # Check flat file: <base>/<name>.md
        if (base / f"{skill_name}.md").exists():
            return True
        # Check directory format: <base>/<name>/SKILL.md
        if (base / skill_name / "SKILL.md").exists():
            return True
        # Check subcategory format: <base>/<category>/<name>.md or <base>/<category>/<name>/SKILL.md
        for category_dir in base.iterdir():
            if category_dir.is_dir():
                if (category_dir / f"{skill_name}.md").exists():
                    return True
                if (category_dir / skill_name / "SKILL.md").exists():
                    return True
        return False

    def get_all_skills_content(self) -> Dict[str, Dict]:
        """Get full content of all skills for export (Project > Learned > Builtin)."""
        if self._skills_cache is None:
            self._build_cache()

        skills_content: Dict[str, Dict[str, Any]] = {"project": {}, "learned": {}, "builtin": {}}

        for category in ["builtin", "learned", "project"]:
            layer_skills = self._get_layer_skills(category)
            for name, path in layer_skills.items():
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                    skills_content[category][name] = {
                        "path": str(path),
                        "content": content,
                    }
                except Exception:
                    continue

        return skills_content

"""IDE Integration Registry."""

import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class IDERegistry:
    """Manage IDE-specific configuration and registration."""

    SUPPORTED_IDES = ["antigravity", "cline", "cursor", "vscode"]

    @staticmethod
    def detect_ide(project_path: Path) -> str:
        """Detect the primary IDE used in the project."""
        if (project_path / ".cursorrules").exists():
            return "cursor"
        if (project_path / ".vscode").exists():
            # Could be vscode or antigravity (which might use vscode settings)
            # Default to vscode if no specific antigravity marker
            return "vscode"
        return "cline"  # Default/Fallback

    def register(self, ide: str, project_path: Path, rules_path: Path):
        """Register the generated rules with the specified IDE."""
        ide = ide.lower()
        if ide not in self.SUPPORTED_IDES:
            logger.warning(f"Unsupported IDE: {ide}")
            return

        logger.info(f"Registering rules for {ide}...")

        if ide == "antigravity":
            self._register_antigravity(project_path, rules_path)
        elif ide == "cline":
            self._register_cline(project_path, rules_path)
        elif ide == "cursor":
            self._register_cursor(project_path, rules_path)
        elif ide == "vscode":
            self._register_vscode(project_path, rules_path)

    def _register_antigravity(self, project_path: Path, rules_path: Path):
        """Register for Antigravity (updates .vscode/settings.json)."""
        vscode_dir = project_path / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        settings_path = vscode_dir / "settings.json"

        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupt {settings_path}, backing up: {e}")
                backup = settings_path.with_suffix(".json.bak")
                shutil.copy2(settings_path, backup)
                settings = {}

        # Hypothetical setting for Antigravity
        try:
            rel = rules_path.relative_to(project_path).as_posix()
        except ValueError:
            rel = str(rules_path)
        settings["antigravity.rulesPath"] = rel

        settings_path.write_text(json.dumps(settings, indent=4), encoding="utf-8")
        logger.info(f"Updated {settings_path}")

    def _register_cline(self, project_path: Path, rules_path: Path):
        """Register for Cline (No-op as it auto-detects .clinerules)."""
        logger.info("Cline auto-detects .clinerules/rules.md. No action needed.")

    def _register_cursor(self, project_path: Path, rules_path: Path):
        """Register for Cursor (Symlink .cursorrules)."""
        # rules_path is typically .clinerules/rules.md
        # Cursor expects .cursorrules in root
        target = project_path / ".cursorrules"

        # If .cursorrules exists and is not a symlink, back it up?
        # Or overwrite?
        # "Cursor/VSCode create symlinks (.cursorrules, AGENTS.md)?"

        try:
            if target.exists() or target.is_symlink():
                target.unlink()

            # Create relative symlink
            try:
                rel_path = rules_path.relative_to(project_path)
            except ValueError:
                rel_path = rules_path
            target.symlink_to(rel_path)
            logger.info(f"Created symlink {target} -> {rel_path}")
        except OSError as e:
            logger.warning(f"Failed to create symlink: {e}. Copying instead.")
            shutil.copy2(rules_path, target)

    def _register_vscode(self, project_path: Path, rules_path: Path):
        """Register for VSCode (Symlink AGENTS.md)."""
        # Some VSCode agents look for AGENTS.md
        target = project_path / "AGENTS.md"

        try:
            if target.exists() or target.is_symlink():
                target.unlink()

            try:
                rel_path = rules_path.relative_to(project_path)
            except ValueError:
                rel_path = rules_path
            target.symlink_to(rel_path)
            logger.info(f"Created symlink {target} -> {rel_path}")
        except OSError as e:
            logger.warning(f"Failed to create symlink: {e}. Copying instead.")
            shutil.copy2(rules_path, target)

import argparse
import logging
import shutil
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from generator.project_analyzer import ProjectAnalyzer
from generator.skills_manager import SkillsManager
from prg_utils.logger import setup_logging

setup_logging(verbose=True)
logger = logging.getLogger("project_rules_generator")

def backup_clinerules(project_path: Path, dry_run: bool = False):
    """Backup .clinerules directory."""
    clinerules = project_path / ".clinerules"
    backup = project_path / ".clinerules.backup"
    
    if not clinerules.exists():
        logger.warning(f".clinerules not found at {clinerules}. Skipping backup.")
        return

    logger.info(f"Backing up {clinerules} to {backup}...")
    if not dry_run:
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(clinerules, backup)

def restore_backup(project_path: Path):
    """Restore .clinerules from backup."""
    clinerules = project_path / ".clinerules"
    backup = project_path / ".clinerules.backup"
    
    if not backup.exists():
        logger.error("Backup not found! Cannot restore.")
        return

    logger.info("Restoring backup...")
    if clinerules.exists():
        shutil.rmtree(clinerules)
    shutil.copytree(backup, clinerules)
    logger.info("Restored.")

def migrate_project(project_path: Path, dry_run: bool = False):
    """Migrate project to local skills architecture."""
    project_path = project_path.resolve()
    logger.info(f"Starting migration for: {project_path}")
    
    if dry_run:
        logger.info("[DRY RUN] Changes will NOT be applied.")

    # 1. Backup
    try:
        backup_clinerules(project_path, dry_run)
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return

    try:
        # 2. Setup new structure
        skills_dir = project_path / "skills"
        builtin_dir = skills_dir / "builtin"
        learned_dir = skills_dir / "learned"
        
        logger.info(f"Creating local skills structure: {skills_dir}")
        if not dry_run:
            builtin_dir.mkdir(parents=True, exist_ok=True)
            learned_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. Copy Builtin Skills
        # We can use SkillDiscovery to find global builtin path
        manager = SkillsManager(project_path=project_path, skills_dir=skills_dir)
        global_builtin = manager.discovery.global_builtin
        
        logger.info(f"Copying builtin skills from {global_builtin} to {builtin_dir}")
        if not dry_run:
            if global_builtin.exists():
                for item in global_builtin.iterdir():
                    dest = builtin_dir / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
            else:
                logger.warning("Global builtin skills not found.")

        # 4. Generate Learned Skills from README
        logger.info("Generating learned skills from README...")
        
        # Analyze project to get tech stack and context
        analyzer = ProjectAnalyzer(project_path)
        context = analyzer.analyze()
        tech_stack = sorted(list(set(sum(context["tech_stack"].values(), []))))
        
        readme_path = project_path / "README.md"
        readme_content = ""
        if readme_path.exists():
            readme_content = readme_path.read_text(encoding="utf-8", errors="replace")
        else:
            logger.warning("README.md not found.")
            
        if not dry_run:
            generated = manager.generate_from_readme(
                readme_content=readme_content,
                tech_stack=tech_stack,
                output_dir=project_path, # SkillsManager will use project_skills_root (./skills) because we passed skills_dir
                project_name=project_path.name,
                project_path=project_path
            )
            logger.info(f"Generated/Adapted skills: {generated}")
        else:
            logger.info(f"[DRY RUN] Would generate skills for: {tech_stack}")

        # 5. Verification
        if not dry_run:
            logger.info("Verifying migration...")
            if not skills_dir.exists():
                raise FileNotFoundError(f"{skills_dir} was not created.")
            if not builtin_dir.exists():
                raise FileNotFoundError(f"{builtin_dir} was not created.")
            
            # Check for at least one skill if tech stack was found
            if tech_stack and not any(learned_dir.iterdir()):
                 # Maybe some tech didn't map to skills, so just warning
                 logger.warning("No learned skills generated (check tech stack mapping).")
            
            logger.info("Migration verified successfully.")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if not dry_run:
            logger.info("Rolling back changes...")
            restore_backup(project_path)
            # Cleanup failed skills dir
            if skills_dir.exists():
                shutil.rmtree(skills_dir)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely migrate to local skills architecture.")
    parser.add_argument("project_path", help="Path to the project to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without changes")
    
    args = parser.parse_args()
    
    migrate_project(Path(args.project_path), args.dry_run)

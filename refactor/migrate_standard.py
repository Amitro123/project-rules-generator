
import shutil
import sys
from pathlib import Path


def merge_directories(src: Path, dst: Path):
    """Recursively merge src directory into dst."""
    if not dst.exists():
        dst.mkdir(parents=True)
    
    for item in src.iterdir():
        dest_path = dst / item.name
        if item.is_dir():
            print(f"   -> Merging directory {item.name}")
            merge_directories(item, dest_path)
            # Remove source dir after successful merge
            try:
                item.rmdir() 
            except OSError:
                pass # Might not be empty if something failed
        else:
            if not dest_path.exists():
                print(f"   -> Moving file {item.name}")
                shutil.move(str(item), str(dest_path))
            else:
                print(f"   ⚠️  Target file {item.name} exists. Skipping.")

def migrate_project(project_path: str = "."):
    """
    Migrate project skills to the standard .clinerules/skills/ location.
    """
    project_path = Path(project_path).resolve()
    print(f"📦 Migrating project: {project_path}")

    clinerules_dir = project_path / ".clinerules"
    clinerules_dir.mkdir(exist_ok=True)

    # 1. Target Directory: .clinerules/skills
    target_skills_dir = clinerules_dir / "skills"
    
    # 2. Source Directory: skills (root)
    source_skills_dir = project_path / "skills"

    # Check if we need to migrate root 'skills'
    if source_skills_dir.exists():
        print(f"found root skills at: {source_skills_dir}")
        merge_directories(source_skills_dir, target_skills_dir)
        try:
            source_skills_dir.rmdir()
            print("🗑️  Removed empty root 'skills/' directory")
        except OSError:
            print("ℹ️  Root 'skills/' not empty, kept.")
    else:
        print("ℹ️  No root 'skills/' directory found.")

    # Check for nesting: .clinerules/skills/skills
    nested_skills = target_skills_dir / "skills"
    if nested_skills.exists() and nested_skills.is_dir():
        print("🔧 Detected nested 'skills/skills'. Fixing...")
        merge_directories(nested_skills, target_skills_dir)
        
        # Remove empty nested dir
        try:
            nested_skills.rmdir()
            print("   ✅ Removed nested 'skills' dir")
        except OSError:
            print("   ⚠️  Could not remove nested 'skills' dir (not empty?)")

    print("\n✅ Migration complete! Skills are now in .clinerules/skills/")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        migrate_project(sys.argv[1])
    else:
        migrate_project()

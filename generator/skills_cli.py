from pathlib import Path
import click
import shutil
import re

def get_skills_root(project_path: str = ".") -> Path:
    """Get the root skills directory."""
    return Path(project_path) / "skills"

def list_skills():
    """List all available skills from the skills/ directory."""
    root = get_skills_root()
    if not root.exists():
        click.echo(f"Skills directory not found at {root}")
        return

    click.echo("\n[Skills] Available Skills:")
    
    # Define layers and their display names
    layers = {
        "builtin": "[Built-in] Skills (Shipped)",
        "awesome": "[Awesome] Skills (Community)",
        "learned": "[Learned] Skills (Project-Specific)"
    }

    for layer, display_name in layers.items():
        layer_path = root / layer
        if layer_path.exists():
            click.echo(f"\n{display_name}")
            skills = sorted([d for d in layer_path.iterdir() if d.is_dir()])
            
            if not skills:
                click.echo("  (none)")
                continue

            for skill_dir in skills:
                skill_file = skill_dir / "SKILL.md"
                desc = ""
                if skill_file.exists():
                    # Try to extract Purpose
                    content = skill_file.read_text(encoding="utf-8")
                    match = re.search(r"## Purpose\n(.*)", content)
                    if match:
                         desc = f"- {match.group(1).strip()}"
                
                click.echo(f"  - {skill_dir.name} {desc}")


def create_skill(name: str, from_readme: str = None):
    """Create a new skill from a template or README."""
    root = get_skills_root()
    learned_dir = root / "learned"
    new_skill_dir = learned_dir / name
    
    if new_skill_dir.exists():
        click.echo(f"[!] Skill '{name}' already exists in learned/.")
        return

    new_skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = new_skill_dir / "SKILL.md"

    # Default Template
    title = name.replace('-', ' ').title()
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
            readme_content = readme_path.read_text(encoding="utf-8")
            # In a real implementation, we'd use LLM to extract.
            # For now, we'll append the README content as context.
            content += f"\n\n## Context (from {readme_path.name})\n\n{readme_content}\n"
            click.echo(f"[i] Included content from {readme_path}")
        else:
             click.echo(f"[!] Warning: README {from_readme} not found.")

    skill_file.write_text(content, encoding="utf-8")
    click.echo(f"[+] Created new skill: {skill_file}")
    click.echo(f"[>] Location: {new_skill_dir}")

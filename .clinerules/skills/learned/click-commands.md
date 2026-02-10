### click-commands
Leverage `click` for consistent and well-documented CLI interfaces.

**Context:** This project utilizes `click` to create a command-line interface. Maintaining consistency in command structure, option handling, and help text is crucial for usability.

**When to use:**
- Adding new subcommands or options to the CLI.
- Modifying existing CLI commands to improve user experience.

**Check for:**
1. Inconsistent option naming conventions (e.g., mixing snake_case and kebab-case).
2. Missing help text for options, making the CLI harder to use.

**Good pattern (from this project):**
```python
# File: main.py
@click.command()
@click.argument("project_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--scan-all", is_flag=True, help="Scan all files, ignoring .gitignore.")
@click.option("--commit", is_flag=True, help="Commit changes to git.")
@click.option("--interactive", is_flag=True, help="Run in interactive mode.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--export-json", is_flag=True, help="Export rules and skills to JSON files.")
@click.option("--export-yaml", is_flag=True, help="Export rules and skills to YAML files.")
@click.option("--save-learned", is_flag=True, help="Save learned skills to disk.")
@click.option("--include-pack", multiple=True, type=str, help="Include a skill pack.")
@click.option("--external-packs-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="Path to external skill packs directory.")
@click.option("--list-skills", is_flag=True, help="List available skills.")
@click.option("--create-skill", type=str, help="Create a new skill with the given name.")
@click.option("--from-readme", is_flag=True, help="Generate skills from README.md.")
@click.option("--ai", type=click.Choice(["claude", "gemini"]), default="claude", help="AI provider to use.")
@click.option("--output", type=click.Path(file_okay=True, dir_okay=False), help="Output file path.")
@click.option("--with-skills", type=str, help="Path to skills.md file.")
@click.option("--auto-generate-skills", is_flag=True, help="Automatically generate skills.")
@click.option("--api-key", type=str, help="API key for the AI provider.")
def main(project_path, scan_all, commit, interactive, verbose, export_json, export_yaml, save_learned, include_pack, external_packs_dir, list_skills, create_skill, from_readme, ai, output, with_skills, auto_generate_skills, api_key):
    """Generate rules.md and skills.md from README.md
    
    Examples:
    \b
        python main.py . --export-json
        python main.py . --include-pack agent-rules
    """
    project_path = Path(project_path).resolve()
    cleanup_awesome_skills()
```

**Anti-pattern to fix:**
```python
# File: main.py
@click.command()
@click.argument("project_path")
@click.option("--json", is_flag=True) # Inconsistent naming and missing help text
def main(project_path, json):
    pass
```

**Action items:**
1. Refactor inconsistent option names to use kebab-case consistently (e.g., `--export-json` instead of `--json` in `main.py`).
2. Add comprehensive help text to all `click.option` and `click.argument` definitions to improve CLI usability (see `main.py`).

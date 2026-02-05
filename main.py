"""CLI orchestrator for project rules and skills generator."""
import sys
from pathlib import Path
import yaml
import click

try:
    from tqdm import tqdm
except ImportError:
    # Fallback to a dummy tqdm
    def tqdm(iterable=None, *args, **kwargs):
        return iterable if iterable else []

from analyzer.readme_parser import parse_readme
from generator.rules_generator import generate_rules
from generator.skills_generator import generate_skills
from utils.file_ops import save_markdown
from utils.git_ops import commit_files, is_git_repo
from utils.exceptions import (
    ProjectRulesGeneratorError,
    READMENotFoundError,
    InvalidREADMEError,
    DetectionFailedError
)


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / 'config.yaml'
    if config_path.exists():
        return yaml.safe_load(config_path.read_text())
    return {
        'llm': {'enabled': False},
        'git': {'auto_commit': True, 'commit_message': 'Auto-generated rules and skills'},
        'generation': {'verbose': True}
    }


from generator.pack_manager import load_external_packs

@click.command()
@click.argument('project_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--scan-all', is_flag=True, help='Scan all subdirectories for projects')
@click.option('--commit/--no-commit', default=True, help='Auto-commit to git')
@click.option('--interactive', '-i', is_flag=True, help='Interactive prompts')
@click.option('--verbose/--quiet', default=True, help='Verbose output')
@click.option('--export-json', is_flag=True, help='Export skills as JSON')
@click.option('--export-yaml', is_flag=True, help='Export skills as YAML')
@click.option('--include-pack', multiple=True, help='Include external skill pack (name or path)')
@click.option('--external-packs-dir', type=click.Path(exists=True, file_okay=False), help='Directory containing external packs')
@click.version_option(version='0.1.0')
def main(project_path, scan_all, commit, interactive, verbose, export_json, export_yaml, include_pack, external_packs_dir):
    """Generate rules.md and skills.md from README.md
    
    Examples:
    \b
        python main.py . --export-json
        python main.py . --include-pack agent-rules
    """
    project_path = Path(project_path).resolve()
    
    if verbose:
        click.echo(f"Project Rules Generator v0.1.0")
        click.echo(f"Target: {project_path}")
    
    try:
        # Load config
        config = load_config()
        
        # Load External Packs
        external_packs = []
        if include_pack or (config.get('packs') and config['packs'].get('enabled')):
            external_packs = load_external_packs(
                include_packs=include_pack,
                config_packs=config.get('packs'),
                external_packs_dir=external_packs_dir,
                verbose=verbose
            )

        # Find README
        readme_path = project_path / 'README.md'
        if not readme_path.exists():
            alternative_readmes = list(project_path.glob('*.md'))
            readme_candidates = [r for r in alternative_readmes if 'readme' in r.name.lower()]
            if readme_candidates:
                readme_path = readme_candidates[0]
            else:
                raise READMENotFoundError(f"No README.md found in {project_path}")
        
        if verbose:
            click.echo(f"README: {readme_path}")
        
        # Parse README
        project_data = parse_readme(readme_path)
        project_name = project_data['name']
        
        if verbose:
            click.echo(f"\nDetected:")
            click.echo(f"   Name: {project_name}")
            click.echo(f"   Tech: {', '.join(project_data['tech_stack']) if project_data['tech_stack'] else 'None detected'}")
            click.echo(f"   Features: {len(project_data['features'])} found")
        
        # Interactive mode
        if interactive:
            click.echo(f"\nProject: {project_data.get('raw_name', project_name)}")
            if project_data['tech_stack']:
                click.echo(f"   Tech stack: {', '.join(project_data['tech_stack'])}")
            if project_data['features']:
                click.echo(f"   Top feature: {project_data['features'][0]}")
            
            if not click.confirm(f"\nContinue generating files?", default=True):
                click.echo("Aborted.")
                sys.exit(0)
        
        # Generate files with progress bar if available
        if verbose:
            click.echo(f"\nGenerating files...")
        
        generated_files = []
        
        with tqdm(total=3, disable=not verbose, desc="Build") as pbar:
             pbar.set_description("Generating Rules")
             rules_content = generate_rules(project_data, config)
             pbar.update(1)
             
             pbar.set_description("Generating Skills")
             # Markdown generation (Default)
             skills_content = generate_skills(project_data, config, project_path, format='markdown', external_packs=external_packs)
             pbar.update(1)
             
             pbar.set_description("Saving Artifacts")
             # Define output paths
             rules_path = project_path / f"{project_name}-rules.md"
             skills_path = project_path / f"{project_name}-skills.md"
             
             save_markdown(rules_path, rules_content)
             save_markdown(skills_path, skills_content)
             generated_files.extend([rules_path, skills_path])

             # Handle exports
             if export_json:
                 json_content = generate_skills(project_data, config, project_path, format='json', external_packs=external_packs)
                 json_path = project_path / f"{project_name}-skills.json"
                 json_path.write_text(json_content, encoding='utf-8')
                 generated_files.append(json_path)

             if export_yaml:
                 yaml_content = generate_skills(project_data, config, project_path, format='yaml', external_packs=external_packs)
                 yaml_path = project_path / f"{project_name}-skills.yaml"
                 yaml_path.write_text(yaml_content, encoding='utf-8')
                 generated_files.append(yaml_path)

             pbar.update(1)
        
        click.echo(f"\nGenerated files:")
        for f in generated_files:
            click.echo(f"   {f}")
        
        # Git commit
        if commit:
            if not is_git_repo(project_path):
                click.echo(f"\nWARNING: Not a git repository, skipping commit")
            else:
                commit_msg = config.get('git', {}).get('commit_message', 'Auto-generated rules and skills')
                user_name = config.get('git', {}).get('commit_user_name')
                user_email = config.get('git', {}).get('commit_user_email')
                
                try:
                    result = commit_files(
                        generated_files, 
                        commit_msg, 
                        project_path,
                        user_name,
                        user_email
                    )
                    click.echo(f"\nCommitted to git")
                    if 'nothing to commit' in result.lower():
                        click.echo(f"   (or files already tracked)")
                except Exception as e:
                    click.echo(f"\nWARNING: Git commit failed: {e}")
                    click.echo(f"   Files were generated, you can commit manually")
        
        click.echo(f"\nDone!")

    except READMENotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("💡 Tip: Make sure README.md exists in the project root.")
        sys.exit(1)
        
    except InvalidREADMEError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("💡 Tip: README should have at least a title and description.")
        sys.exit(1)
        
    except ProjectRulesGeneratorError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
        
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

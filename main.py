"""CLI orchestrator for project rules and skills generator."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from pathlib import Path
import yaml
import click
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

try:
    from tqdm import tqdm
except ImportError:
    # Fallback to a dummy tqdm that supports context manager
    class tqdm:
        def __init__(self, iterable=None, *args, **kwargs):
            self.iterable = iterable or []
        
        def __iter__(self):
            return iter(self.iterable)
            
        def __enter__(self):
            return self
            
        def __exit__(self, *args):
            pass
            
        def update(self, *args):
            pass
            
        def set_description(self, *args):
            pass

from analyzer.readme_parser import parse_readme
from generator.rules_generator import generate_rules
from generator.skills_generator import generate_skills
from prg_utils.file_ops import save_markdown
from prg_utils.git_ops import commit_files, is_git_repo
from prg_utils.exceptions import (
    ProjectRulesGeneratorError,
    READMENotFoundError,
    InvalidREADMEError,
    DetectionFailedError
)
from pydantic import ValidationError
from prg_utils.config_schema import validate_config
from prg_utils.logger import setup_logging


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / 'config.yaml'
    raw_config = {}
    if config_path.exists():
        raw_config = yaml.safe_load(config_path.read_text()) or {}
    
    # Validate and fill defaults
    config_model = validate_config(raw_config)
    return config_model.model_dump()


def setup_orchestrator(config):
    """Initialize and configure SkillOrchestrator."""
    from generator.orchestrator import SkillOrchestrator
    from generator.sources.builtin import BuiltinSkillsSource
    from generator.sources.learned import LearnedSkillsSource
    from generator.sources.awesome import AwesomeSkillsSource

    orchestrator = SkillOrchestrator(config)
    orchestrator.register_source(BuiltinSkillsSource(config))
    orchestrator.register_source(LearnedSkillsSource(config))
    if config.get('skill_sources', {}).get('awesome', {}).get('enabled'):
         orchestrator.register_source(AwesomeSkillsSource(config))
    return orchestrator


from generator.pack_manager import load_external_packs
from generator.skills_manager import SkillsManager

@click.command()
@click.argument('project_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--scan-all', is_flag=True, help='Scan all subdirectories for projects')
@click.option('--commit/--no-commit', default=True, help='Auto-commit to git')
@click.option('--interactive', '-i', is_flag=True, help='Interactive prompts')
@click.option('--verbose/--quiet', default=True, help='Verbose output')
@click.option('--export-json', is_flag=True, help='Export skills as JSON')
@click.option('--export-yaml', is_flag=True, help='Export skills as YAML')
@click.option('--save-learned', is_flag=True, help='Save newly generated skills to learned library')
@click.option('--include-pack', multiple=True, help='Include external skill pack (name or path)')
@click.option('--external-packs-dir', type=click.Path(exists=True, file_okay=False), help='Directory containing external packs')
@click.option('--list-skills', is_flag=True, help='List all available skills from all sources')
@click.option('--create-skill', help='Create a new learned skill with the given name')
@click.option('--from-readme', type=click.Path(exists=True, dir_okay=False), help='Use README as context for new skill')
@click.option('--ai', is_flag=True, help='Use AI to generate skill content (requires GEMINI_API_KEY)')
@click.option('--output', type=click.Path(), default='.clinerules', help='Output file (unified rules + skills)')
@click.option('--with-skills', is_flag=True, default=True, help='Include skills in output')
@click.option('--auto-generate-skills', is_flag=True, help='Auto-detect and generate skills (requires --ai)')
@click.option('--api-key', help='Gemini API Key (overrides GEMINI_API_KEY env var)')
@click.version_option(version='0.1.0')
def main(project_path, scan_all, commit, interactive, verbose, export_json, export_yaml, save_learned, include_pack, external_packs_dir, list_skills, create_skill, from_readme, ai, output, with_skills, auto_generate_skills, api_key):
    """Generate rules.md and skills.md from README.md
    
    Examples:
    \b
        python main.py . --export-json
        python main.py . --include-pack agent-rules
    """
    project_path = Path(project_path).resolve()
    
    if verbose:
        setup_logging(verbose=True)
        click.echo(f"Project Rules Generator v0.1.0")
        click.echo(f"Target: {project_path}")
    else:
        setup_logging(verbose=False)
    
    # Handle API Key
    if api_key:
        os.environ['GEMINI_API_KEY'] = api_key

    try:
        # Load config
        config = load_config()
        
        # Override config with CLI flags
        if save_learned:
             # Ensure structure exists
             if 'skill_sources' not in config: config['skill_sources'] = {}
             if 'learned' not in config['skill_sources']: config['skill_sources']['learned'] = {}
             config['skill_sources']['learned']['auto_save'] = True

        # Skills Manager Logic
        skills_dir = project_path / "skills"
        
        if create_skill:
            manager = SkillsManager()
            try:
                path = manager.create_skill(
                    create_skill, 
                    from_readme=from_readme, 
                    project_path=str(project_path),
                    use_ai=ai
                )
                click.echo(f"✨ Created new skill '{path.name}' in {path}")
            except Exception as e:
                click.echo(f"❌ Failed to create skill: {e}", err=True)
                sys.exit(1)
            sys.exit(0)

        if list_skills:
            # Use SkillsManager for raw listing of available skills
            manager = SkillsManager()
            skills_map = manager.list_skills()

            total_skills = sum(len(s) for s in skills_map.values())
            click.echo(f"\nAvailable Skills ({total_skills} found):")

            for category, skills in skills_map.items():
                if skills:
                    click.echo(f"\n📁 {category.title()}:")
                    for skill in skills:
                        click.echo(f"  - {skill}")
            sys.exit(0)

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
        readme_candidates = ['README.md', 'README.rst', 'README.txt', 'README']
        readme_path = None
        for candidate in readme_candidates:
            if (project_path / candidate).exists():
                readme_path = project_path / candidate
                break
        
        # Interactive README Generation
        from generator.readme_generator import is_readme_minimal, generate_readme_interactively
        
        # If no README or minimal, and we want to try generating one
        if not readme_path or is_readme_minimal(readme_path or (project_path / 'README.md')):
            if interactive:
                try:
                    click.echo("\n⚠️  README is missing or minimal.")
                    content = generate_readme_interactively(project_path, ai)
                    
                    if not readme_path:
                        readme_path = project_path / 'README.md'
                    
                    readme_path.write_text(content, encoding='utf-8')
                    click.echo(f"✅ README.md created/updated and saved to {readme_path}\n")
                except click.Abort:
                    click.echo("⚠️  Skipping README generation. Analysis will be limited.")
            else:
                if not readme_path:
                    click.echo("⚠️  No README found. Context will be limited.")
                    click.echo("💡 Tip: Use --interactive to auto-generate a professional README.")
                else:
                    click.echo(f"⚠️  README ({readme_path.name}) is minimal. Context may be limited.")
                    click.echo("💡 Tip: Use --interactive to improve it.")

        # Fallback if still no README (create dummy or skip)
        if not readme_path or not readme_path.exists():
            # If we are here, we don't have a readme and user skipped/didnt ask for generation
            # We must proceed carefully.
            readme_path = None

        if readme_path and readme_path.exists():
            # Parse README
            if verbose:
                click.echo(f"README: {readme_path}")
            project_data = parse_readme(readme_path)
        else:
            # Create minimal project data from structure
            click.echo("ℹ️  Proceeding with structure-only analysis...")
            from generator.project_analyzer import ProjectAnalyzer
            analyzer = ProjectAnalyzer(project_path)
            context = analyzer.analyze()
            project_data = {
                'name': project_path.name,
                'tech_stack': sorted(list(set(sum(context['tech_stack'].values(), [])))),
                'features': [],
                'description': "No README provided.",
                'raw_name': project_path.name
            }
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
        
        with tqdm(total=4, disable=not verbose, desc="Build") as pbar:
             pbar.set_description("Generating Rules")
             rules_content = generate_rules(project_data, config)
             pbar.update(1)
             
             pbar.set_description("Processing Skills")
             skills_manager = SkillsManager()
             
             # Auto-generate skills if requested
             if auto_generate_skills and ai:
                 try:
                     from generator.project_analyzer import ProjectAnalyzer
                     analyzer = ProjectAnalyzer(project_path)
                     analysis = analyzer.analyze()
                     workflows = analysis.get('workflows', [])
                     
                     for wf in workflows:
                         skill_name = wf['name'].lower().replace(' ', '-')
                         # Check if exists
                         skill_dir = skills_manager.learned_path / skill_name
                         if not skill_dir.exists():
                             click.echo(f"\n🤖 Auto-generating skill: {skill_name}")
                             try:
                                 skills_manager.create_skill(skill_name, project_path=str(project_path), use_ai=True)
                             except Exception as e:
                                 click.echo(f"Warning: Failed to auto-gen skill {skill_name}: {e}")
                 except Exception as e:
                     click.echo(f"Warning: Auto-generation failed: {e}")

             # Extract Triggers
             triggers = []
             if with_skills:
                 triggers = skills_manager.extract_auto_triggers()
             pbar.update(1)
             
             pbar.set_description("Unified Export (.clinerules)")
             # Build Unified Content
             unified_content = rules_content + "\n\n# 🧠 Agent Skills\n\n"
             
             if triggers:
                 unified_content += "## Active Skill Triggers\n"
                 for t in triggers:
                     unified_content += f"- **{t['skill']}** ({t['category']}): {', '.join(t['conditions'])}\n"
                 unified_content += "\n"
                 
                 # Embed full skill content (optional, but requested 'Unified')
                 # For .clinerules, having the full context is good.
                 unified_content += "## Skill Definitions\n"
                 all_skills = skills_manager.get_all_skills_content()
                 for t in triggers:
                     skill_name = t['skill']
                     category = t['category']
                     if skill_name in all_skills.get(category, {}):
                         content = all_skills[category][skill_name]['content']
                         # Downgrade headers in content?
                         unified_content += f"\n### Skill: {skill_name}\n{content}\n"

             output_path = project_path / output
             save_markdown(output_path, unified_content)
             generated_files.append(output_path)
             pbar.update(1)

             # Legacy/Separate Generation (Orchestrated)
             pbar.set_description("Saving Separate Artifacts")
             # Initialize Orchestrator
             from generator.types import SkillFile
             from generator.sources.learned import LearnedSkillsSource
             from generator.renderers import get_renderer
             
             orchestrator = setup_orchestrator(config)
             
             # Run orchestration
             skills = orchestrator.orchestrate(project_data, str(project_path))
             
             # Save learned skills if requested
             if save_learned:
                 learned_source = next((s for s in orchestrator.sources if isinstance(s, LearnedSkillsSource)), None)
                 if learned_source:
                     # print(f"Saving {len(skills)} skills to learned library...")
                     for skill in skills:
                         learned_source.save_skill(skill)
             
             # Create SkillFile wrapper
             from analyzer.project_type_detector import detect_project_type_from_data
             type_info = detect_project_type_from_data(project_data, str(project_path))
             
             skill_file = SkillFile(
                project_name=project_name,
                project_type=type_info['primary_type'],
                skills=skills,
                confidence=type_info['confidence'],
                tech_stack=project_data.get('tech_stack', []),
                description=project_data.get('description', '')
             )
             
             # Render Markdown
             skills_content = get_renderer('markdown').render(skill_file)
             
             # Define output paths
             # rules_path = project_path / f"{project_name}-rules.md" # Replaced by .clinerules
             skills_path = project_path / f"{project_name}-skills.md"
             
             # save_markdown(rules_path, rules_content) # Optional: keep generating rules separately? User didn't strictly forbid.
             # I'll enable it for backward compat if output != rules.md
             if output != f"{project_name}-rules.md":
                 save_markdown(project_path / f"{project_name}-rules.md", rules_content)
                 generated_files.append(project_path / f"{project_name}-rules.md")

             save_markdown(skills_path, skills_content)
             generated_files.append(skills_path)

             # Handle exports
             if export_json:
                 json_content = get_renderer('json').render(skill_file)
                 json_path = project_path / f"{project_name}-skills.json"
                 json_path.write_text(json_content, encoding='utf-8')
                 generated_files.append(json_path)

             if export_yaml:
                 yaml_content = get_renderer('yaml').render(skill_file)
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

    except ValidationError as e:
        click.echo(f"❌ Configuration Error: {e}", err=True)
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

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

# Enhanced modules (Phase 1-4)
from generator.parsers.enhanced_parser import EnhancedProjectParser
from generator.parsers.dependency_parser import DependencyParser
from generator.analyzers.structure_analyzer import StructureAnalyzer
from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher
from generator.extractors.code_extractor import CodeExampleExtractor
from generator.prompts.skill_generation import build_skill_prompt
from generator.storage.skill_paths import SkillPathManager
from generator.outputs.clinerules_generator import generate_clinerules, generate_clinerules_with_inline
from generator.constitution_generator import generate_constitution
from generator.incremental_analyzer import IncrementalAnalyzer


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / 'config.yaml'
    raw_config = {}
    if config_path.exists():
        raw_config = yaml.safe_load(config_path.read_text()) or {}
    
    # Validate and fill defaults
    config_model = validate_config(raw_config)
    return config_model.model_dump()

def cleanup_awesome_skills():
    """Remove deprecated awesome-skills directory."""
    try:
        import shutil
        awesome_dir = Path.home() / ".project-rules-generator" / "awesome-skills"
        if awesome_dir.exists():
            shutil.rmtree(awesome_dir)
    except Exception:
        pass



def setup_orchestrator(config):
    """Initialize and configure SkillOrchestrator."""
    from generator.orchestrator import SkillOrchestrator
    from generator.sources.builtin import BuiltinSkillsSource
    from generator.sources.learned import LearnedSkillsSource
    
    orchestrator = SkillOrchestrator(config)
    orchestrator.register_source(BuiltinSkillsSource(config))
    orchestrator.register_source(LearnedSkillsSource(config))
    return orchestrator


from generator.pack_manager import load_external_packs
from generator.skills_manager import SkillsManager


class DefaultGroup(click.Group):
    """Click group that delegates to a default command when none is given."""

    def __init__(self, *args, default_cmd='analyze', **kwargs):
        super().__init__(*args, **kwargs)
        self.default_cmd = default_cmd

    def parse_args(self, ctx, args):
        # Let group-level flags (--help, --version) pass through
        if args and args[0] not in self.commands and args[0] not in ('--help', '--version', '-h'):
            args = [self.default_cmd] + list(args)
        elif not args:
            args = [self.default_cmd]
        return super().parse_args(ctx, args)


@click.group(cls=DefaultGroup, default_cmd='analyze')
@click.version_option(version='0.1.0')
def cli():
    """Project Rules Generator - Generate rules.md and skills.md from README.md"""
    pass


@cli.command(name='analyze')
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
@click.option('--output', type=click.Path(file_okay=False), default='.clinerules', help='Output directory (default: .clinerules)')
@click.option('--with-skills', is_flag=True, default=True, help='Include skills in output')
@click.option('--auto-generate-skills', is_flag=True, help='Auto-detect and generate skills (requires --ai)')
@click.option('--api-key', help='Gemini API Key (overrides GEMINI_API_KEY env var)')
@click.option('--constitution', is_flag=True, help='Generate constitution.md with project-specific coding principles')
@click.option('--merge', is_flag=True, help='Preserve existing skill files, only add new ones')
@click.option('--mode', type=click.Choice(['manual', 'ai', 'constitution']), default=None, help='Explicit mode (manual=no AI, ai=auto-generate+AI, constitution=adds constitution.md)')
@click.option('--incremental', is_flag=True, help='Only regenerate changed sections (skip if nothing changed)')
def analyze(project_path, scan_all, commit, interactive, verbose, export_json, export_yaml, save_learned, include_pack, external_packs_dir, list_skills, create_skill, from_readme, ai, output, with_skills, auto_generate_skills, api_key, constitution, merge, mode, incremental):
    """Analyze project and generate rules.md and skills.md from README.md

    Examples:
    \b
        python main.py . --export-json
        python main.py . --include-pack agent-rules
        python main.py . --incremental
    """
    project_path = Path(project_path).resolve()
    cleanup_awesome_skills()

    # Handle --mode shortcut
    if mode == 'ai':
        auto_generate_skills = True
        ai = True
    elif mode == 'constitution':
        constitution = True
    # mode == 'manual' changes nothing (no AI)

    # Create output directory structure
    output_dir = project_path / output
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'skills' / 'builtin').mkdir(parents=True, exist_ok=True)
    (output_dir / 'skills' / 'learned').mkdir(parents=True, exist_ok=True)

    # Incremental mode: check for changes before doing heavy work
    inc_analyzer = IncrementalAnalyzer(project_path, output_dir) if incremental else None
    if inc_analyzer:
        changed_sections = inc_analyzer.detect_changes()
        if not changed_sections:
            click.echo("No changes detected. Skipping regeneration. (use without --incremental to force)")
            sys.exit(0)
        if verbose:
            click.echo(f"Incremental: changed sections: {', '.join(sorted(changed_sections))}")

    if verbose:
        setup_logging(verbose=True)
        click.echo(f"Project Rules Generator v0.1.0")
        click.echo(f"Target: {project_path}")
    else:
        setup_logging(verbose=False)

    # Handle API Key
    if api_key:
        os.environ['GEMINI_API_KEY'] = api_key
        if verbose:
            click.echo("Using API key from --api-key flag")

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
        from generator.interactive import create_readme_interactive, show_generated_files
        
        # If no README or minimal, and we want to try generating one
        if not readme_path or (readme_path and is_readme_minimal(readme_path)):
            if interactive:
                try:
                    # New Rich UI Flow
                    user_input_data = create_readme_interactive(project_path)
                    
                    # Generate content using AI or Template based on 'ai' flag
                    # We reuse _generate_readme_with_llm / _generate_readme_template from readme_generator
                    # but we need to pass the collected data
                    
                    # NOTE: generate_readme_interactively did both prompt + generation.
                    # We disjointed them. Now we have inputs.
                    # We need to run generation.
                    from generator.readme_generator import generate_readme_with_llm, generate_readme_template
                    
                    # Need context for generation
                    from generator.project_analyzer import ProjectAnalyzer
                    analyzer = ProjectAnalyzer(project_path)
                    context = analyzer.analyze()
                    
                    if ai:
                        click.echo("🤖 Generating README with AI...\n")
                        content = generate_readme_with_llm(user_input_data, context)
                    else:
                        content = generate_readme_template(user_input_data, context)
                    
                    if not readme_path:
                        readme_path = project_path / 'README.md'
                    
                    readme_path.write_text(content, encoding='utf-8')
                    click.echo(f"✅ README.md created/updated and saved to {readme_path}\n")
                    
                except Exception as e:
                     click.echo(f"⚠️  README generation failed: {e}")
                     # Fallback to structure analysis if readme gen failed
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
                'raw_name': project_path.name,
                'readme_path': None
            }
        project_name = project_data['name']
        
        if verbose:
            click.echo(f"\nDetected:")
            click.echo(f"   Name: {project_name}")
            click.echo(f"   Tech: {', '.join(project_data['tech_stack']) if project_data['tech_stack'] else 'None detected'}")
            click.echo(f"   Features: {len(project_data['features'])} found")
        
        # Interactive mode confirmation for rules generation
        if interactive:
            from rich.prompt import Confirm
            from generator.utils import flush_input
            # Fixed Bug #1: Ensure single prompt
            flush_input()
            if not Confirm.ask(f"Continue generating .clinerules for [bold]{project_name}[/bold]?", default=True):
                 click.echo("Aborted.")
                 sys.exit(0)
        
        # Generate files with progress bar if available
        if verbose:
            click.echo(f"\nGenerating files...")
        
        generated_files = []
        
        with tqdm(total=4, disable=not verbose, desc="Build") as pbar:
             pbar.set_description("Analyzing Project")
             # Always run enhanced parser for project-specific rules
             enhanced_context = None
             try:
                 enhanced_parser = EnhancedProjectParser(project_path)
                 enhanced_context = enhanced_parser.extract_full_context()
             except Exception as e:
                 if verbose:
                     click.echo(f"   Enhanced analysis unavailable: {e}")

             # Constitution generation (before rules so it appears early in output)
             if constitution and enhanced_context:
                 pbar.set_description("Generating Constitution")
                 constitution_content = generate_constitution(
                     project_name, enhanced_context, project_path=project_path
                 )
                 constitution_path = output_dir / 'constitution.md'
                 constitution_path.write_text(constitution_content, encoding='utf-8')
                 generated_files.append(constitution_path)
                 if verbose:
                     click.echo(f"   Generated constitution.md")
             elif constitution and not enhanced_context:
                 if verbose:
                     click.echo(f"   Skipping constitution (enhanced analysis unavailable)")

             pbar.set_description("Generating Rules")
             rules_content = generate_rules(project_data, config, enhanced_context=enhanced_context)
             pbar.update(1)

             pbar.set_description("Processing Skills")
             skills_manager = SkillsManager()

             # Enhanced auto-generate skills using new Phase 1-4 modules
             enhanced_selected_skills = set()
             if auto_generate_skills:
                 try:
                     # Use already-extracted enhanced_context, or extract if missing
                     if enhanced_context is None:
                         enhanced_parser = EnhancedProjectParser(project_path)
                         enhanced_context = enhanced_parser.extract_full_context()

                     detected_tech = enhanced_context.get('metadata', {}).get('tech_stack', [])
                     project_type = enhanced_context.get('metadata', {}).get('project_type', 'unknown')

                     if verbose:
                         click.echo(f"\n   Enhanced Analysis:")
                         click.echo(f"   Project Type: {project_type}")
                         click.echo(f"   Tech Stack: {', '.join(detected_tech)}")
                         dep_count = len(enhanced_context.get('dependencies', {}).get('python', []))
                         dep_count += len(enhanced_context.get('dependencies', {}).get('node', []))
                         click.echo(f"   Dependencies: {dep_count} parsed")
                         test_info = enhanced_context.get('test_patterns', {})
                         if test_info.get('framework'):
                             click.echo(f"   Tests: {test_info['framework']} ({test_info.get('test_files', 0)} files)")

                     # Step 2: Match skills using EnhancedSkillMatcher
                     enhanced_matcher = EnhancedSkillMatcher()
                     enhanced_selected_skills = enhanced_matcher.match_skills(
                         detected_tech=detected_tech,
                         project_context=enhanced_context,
                     )

                     if verbose:
                         click.echo(f"   Matched Skills: {len(enhanced_selected_skills)}")
                         for s in sorted(enhanced_selected_skills):
                             click.echo(f"     - {s}")

                     # Step 3: Ensure SkillPathManager directories exist
                     SkillPathManager.ensure_setup()

                     # Step 4: Generate high-quality skills with LLM for learned skills
                     if ai:
                         extractor = CodeExampleExtractor()

                         for skill_ref in sorted(enhanced_selected_skills):
                             if not skill_ref.startswith('learned/'):
                                 continue

                             # Check if skill already exists
                             existing_path = SkillPathManager.get_skill_path(skill_ref)
                             if existing_path and existing_path.exists():
                                 continue

                             # Extract code examples for this skill
                             skill_topic = skill_ref.split('/')[-1]
                             examples = extractor.extract_examples_for_skill(
                                 project_path, skill_topic, detected_tech
                             )

                             # Build enhanced prompt
                             prompt = build_skill_prompt(
                                 skill_topic=skill_topic,
                                 project_name=project_name,
                                 context=enhanced_context,
                                 code_examples=examples,
                                 detected_patterns=enhanced_context.get('structure', {}).get('patterns', []),
                                 project_path=project_path,
                             )

                             try:
                                 from generator.llm_skill_generator import LLMSkillGenerator
                                 llm_gen = LLMSkillGenerator()
                                 skill_content = llm_gen.generate_content(prompt, max_tokens=2000)

                                 # Save using SkillPathManager
                                 parts = skill_ref.split('/')
                                 category = parts[1] if len(parts) >= 3 else 'general'
                                 SkillPathManager.save_learned_skill(
                                     {'name': skill_topic, 'content': skill_content},
                                     category
                                 )
                                 click.echo(f"   💾 Generated: {skill_ref}")
                             except Exception as e:
                                 click.echo(f"   ⚠️  Failed to generate {skill_ref}: {e}")

                 except Exception as e:
                     click.echo(f"Warning: Enhanced auto-generation failed: {e}")
                     if verbose:
                         import traceback
                         traceback.print_exc()

             # Extract Triggers
             triggers = []
             if with_skills:
                 triggers = skills_manager.extract_auto_triggers()
             pbar.update(1)
             
             pbar.set_description("Unified Export (.clinerules/)")
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
                         unified_content += f"\n### Skill: {skill_name}\n{content}\n"

             # If enhanced matching was done, also generate lightweight clinerules
             if enhanced_selected_skills:
                 lightweight_yaml = generate_clinerules(
                     project_name, enhanced_selected_skills, enhanced_context,
                     output_dir=output_dir,
                 )
                 # Append as YAML reference block
                 unified_content += f"\n\n<!-- Lightweight Skill References\n{lightweight_yaml}-->\n"

                 # Save standalone lightweight clinerules.yaml inside output dir
                 lightweight_path = output_dir / 'clinerules.yaml'
                 lightweight_path.write_text(lightweight_yaml, encoding='utf-8')
                 generated_files.append(lightweight_path)
                 if verbose:
                     click.echo(f"   Generated clinerules.yaml ({len(enhanced_selected_skills)} skills)")

                 # Copy skill files into output_dir/skills/
                 import shutil
                 existing_skill_files = set()
                 if merge and (output_dir / 'skills').exists():
                     # Collect existing skill files for merge logic
                     for subdir in ('builtin', 'learned'):
                         skill_subdir = output_dir / 'skills' / subdir
                         if skill_subdir.exists():
                             for f in skill_subdir.iterdir():
                                 if f.is_file():
                                     existing_skill_files.add(f.name)

                 for skill_ref in sorted(enhanced_selected_skills):
                     skill_path = SkillPathManager.get_skill_path(skill_ref)
                     if skill_path and skill_path.exists():
                         if skill_ref.startswith('builtin/'):
                             dest = output_dir / 'skills' / 'builtin' / skill_path.name
                         elif skill_ref.startswith('learned/'):
                             dest = output_dir / 'skills' / 'learned' / skill_path.name
                         else:
                             continue
                         shutil.copy2(skill_path, dest)

             # Write rules.md into output directory (with incremental merge if applicable)
             rules_path = output_dir / 'rules.md'
             if inc_analyzer and rules_path.exists():
                 existing_rules = rules_path.read_text(encoding='utf-8')
                 unified_content = IncrementalAnalyzer.merge_rules(
                     existing_rules, unified_content, changed_sections
                 )
             save_markdown(rules_path, unified_content)
             generated_files.append(rules_path)
             pbar.update(1)

             # Orchestrated skill generation
             pbar.set_description("Saving Skill Artifacts")
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

             # Render Markdown skills index
             skills_content = get_renderer('markdown').render(skill_file)

             # Write skills index into output directory
             skills_index_path = output_dir / 'skills' / 'index.md'
             save_markdown(skills_index_path, skills_content)
             generated_files.append(skills_index_path)

             # Handle exports (into output_dir/skills/)
             if export_json:
                 json_content = get_renderer('json').render(skill_file)
                 json_path = output_dir / 'skills' / 'index.json'
                 json_path.write_text(json_content, encoding='utf-8')
                 generated_files.append(json_path)

             if export_yaml:
                 yaml_content = get_renderer('yaml').render(skill_file)
                 yaml_path = output_dir / 'skills' / 'index.yaml'
                 yaml_path.write_text(yaml_content, encoding='utf-8')
                 generated_files.append(yaml_path)

             pbar.update(1)
        
        if interactive:
            # Final stats for rich UI
            # We need to track where skills came from.
            # Currently logic is scattered.
            # Ideally SkillsManager or SkillMatcher should return source info.
            
            # Hack for now: Count based on source attribute if we preserved it, 
            # or just dummy count for the UI demo since we don't have full tracking passed back easily yet.
            # Users request explicitly asked for "Skills Breakdown".
            
            # Let's try to get it from `skills` list which contains Skill objects
            skills_stats = {'learned': 0, 'builtin': 0, 'generated': 0}
            for s in skills:
                if hasattr(s, 'source'):
                    if s.source == 'learned': skills_stats['learned'] += 1
                    elif s.source == 'builtin': skills_stats['builtin'] += 1
                    elif s.source == 'generated': skills_stats['generated'] += 1
                    else: skills_stats['generated'] += 1 # Default

            show_generated_files(generated_files, skills_stats)
        else:
            click.echo(f"\nGenerated files:")
            for f in generated_files:
                click.echo(f"   {f}")
        
        # Git commit
        if commit:
            if not is_git_repo(project_path):
                # Using rich console if interactive?
                if interactive:
                     # Warn but don't look like error
                     pass 
                else:
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
        
        # Save incremental cache
        if inc_analyzer:
            inc_analyzer.save_hash(inc_analyzer.compute_project_hash())
            if verbose:
                click.echo("   Saved incremental cache")

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


@cli.command(name='design')
@click.argument('description')
@click.option('--project-path', type=click.Path(exists=True, file_okay=False), default='.', help='Project directory')
@click.option('--output', '-o', type=click.Path(), default='DESIGN.md', help='Output file (default: DESIGN.md)')
@click.option('--api-key', help='Gemini API Key (overrides GEMINI_API_KEY env var)')
@click.option('--verbose/--quiet', default=True, help='Verbose output')
def design(description, project_path, output, api_key, verbose):
    """Generate a technical design document (Stage 1 of two-stage planning).

    Examples:
    \b
        python main.py design "Add authentication to API"
        python main.py design "Add rate limiting middleware" --output docs/DESIGN.md
    """
    project_path = Path(project_path).resolve()

    if api_key:
        os.environ['GEMINI_API_KEY'] = api_key

    if verbose:
        click.echo(f"Project Rules Generator v0.1.0 — Design Generator")
        click.echo(f"Request: {description}")
        click.echo(f"Project: {project_path}")

    # Gather project context
    enhanced_context = None
    try:
        from generator.parsers.enhanced_parser import EnhancedProjectParser
        parser = EnhancedProjectParser(project_path)
        enhanced_context = parser.extract_full_context()
        if verbose:
            meta = enhanced_context.get('metadata', {})
            click.echo(f"Context: {meta.get('project_type', 'unknown')} ({', '.join(meta.get('tech_stack', []))})")
    except Exception as exc:
        if verbose:
            click.echo(f"Context extraction skipped: {exc}")

    from generator.design_generator import DesignGenerator

    generator = DesignGenerator(api_key=os.getenv('GEMINI_API_KEY'))
    if verbose:
        click.echo("Generating design...")

    design_obj = generator.generate_design(
        description,
        project_context=enhanced_context,
        project_path=project_path,
    )

    design_md = design_obj.to_markdown()

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_path / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(design_md, encoding='utf-8')

    click.echo(f"\nDesign: {design_obj.title}")
    click.echo(f"  Decisions: {len(design_obj.architecture_decisions)}")
    click.echo(f"  API contracts: {len(design_obj.api_contracts)}")
    click.echo(f"  Data models: {len(design_obj.data_models)}")
    click.echo(f"  Success criteria: {len(design_obj.success_criteria)}")
    click.echo(f"Written to: {output_path}")


@cli.command(name='plan')
@click.argument('task_description', required=False, default=None)
@click.option('--from-design', type=click.Path(exists=True, dir_okay=False), default=None, help='Generate plan from a DESIGN.md file')
@click.option('--project-path', type=click.Path(exists=True, file_okay=False), default='.', help='Project directory')
@click.option('--output', '-o', type=click.Path(), default='PLAN.md', help='Output file for the plan (default: PLAN.md)')
@click.option('--api-key', help='Gemini API Key (overrides GEMINI_API_KEY env var)')
@click.option('--verbose/--quiet', default=True, help='Verbose output')
def plan(task_description, from_design, project_path, output, api_key, verbose):
    """Break down a task into subtasks and generate PLAN.md.

    Can generate from a task description or from an existing DESIGN.md.

    Examples:
    \b
        python main.py plan "Add authentication to API"
        python main.py plan --from-design DESIGN.md
        python main.py plan "Refactor database layer" --output docs/PLAN.md
    """
    if not task_description and not from_design:
        click.echo("Error: Provide a TASK_DESCRIPTION or --from-design.", err=True)
        sys.exit(1)

    project_path = Path(project_path).resolve()

    if api_key:
        os.environ['GEMINI_API_KEY'] = api_key

    if verbose:
        click.echo(f"Project Rules Generator v0.1.0 — Task Planner")
        if from_design:
            click.echo(f"From design: {from_design}")
        else:
            click.echo(f"Task: {task_description}")
        click.echo(f"Project: {project_path}")

    # Gather project context if available
    enhanced_context = None
    try:
        from generator.parsers.enhanced_parser import EnhancedProjectParser
        parser = EnhancedProjectParser(project_path)
        enhanced_context = parser.extract_full_context()
        if verbose:
            meta = enhanced_context.get('metadata', {})
            click.echo(f"Context: {meta.get('project_type', 'unknown')} ({', '.join(meta.get('tech_stack', []))})")
    except Exception as exc:
        if verbose:
            click.echo(f"Context extraction skipped: {exc}")

    from generator.task_decomposer import TaskDecomposer

    decomposer = TaskDecomposer(api_key=os.getenv('GEMINI_API_KEY'))
    if verbose:
        click.echo("Decomposing task...")

    if from_design:
        subtasks = decomposer.from_design(
            Path(from_design),
            project_context=enhanced_context,
        )
        # Use the design title as user_task for the plan header
        from generator.design_generator import Design
        design_obj = Design.from_markdown(Path(from_design).read_text(encoding='utf-8'))
        user_task_label = design_obj.title
    else:
        subtasks = decomposer.decompose(
            task_description,
            project_context=enhanced_context,
            project_path=project_path,
        )
        user_task_label = task_description

    plan_md = decomposer.generate_plan_md(subtasks, user_task=user_task_label)

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_path / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(plan_md, encoding='utf-8')

    click.echo(f"\nGenerated {len(subtasks)} subtasks")
    click.echo(f"Plan written to: {output_path}")
    click.echo(f"Estimated time: {sum(t.estimated_minutes for t in subtasks)} minutes")


# Backward-compatible alias so existing code that imports `main` still works
main = analyze


if __name__ == '__main__':
    cli()

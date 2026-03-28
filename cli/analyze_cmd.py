"""Analyzer module for project rules generator."""

import os
import sys
from pathlib import Path

import click
import yaml

try:
    from tqdm import tqdm
except ImportError:
    # Fallback to a dummy tqdm
    class tqdm:  # type: ignore[no-redef]
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


from pydantic import ValidationError

from cli._version import __version__
from cli.analyze_quality import run_quality_check
from cli.utils import detect_provider, set_api_key_env
from generator.analyzers.readme_parser import parse_readme
from generator.constitution_generator import generate_constitution
from generator.extractors.code_extractor import CodeExampleExtractor
from generator.incremental_analyzer import IncrementalAnalyzer
from generator.outputs.clinerules_generator import generate_clinerules
from generator.pack_manager import load_external_packs

# Enhanced modules
from generator.parsers.enhanced_parser import EnhancedProjectParser
from generator.prompts.skill_generation import build_skill_prompt
from generator.rules_generator import generate_rules
from generator.skills.enhanced_skill_matcher import EnhancedSkillMatcher
from generator.skills_manager import SkillsManager
from generator.storage.skill_paths import SkillPathManager
from prg_utils.config_schema import validate_config
from prg_utils.exceptions import InvalidREADMEError, ProjectRulesGeneratorError, READMENotFoundError
from prg_utils.file_ops import save_markdown
from prg_utils.git_ops import commit_files, is_git_repo
from prg_utils.logger import setup_logging


# Helper Functions
def load_config():
    """Load configuration from config.yaml."""
    # Adjusted path for refactor module
    config_path = Path(__file__).parent.parent / "config.yaml"
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
    except OSError:
        pass


def _handle_skill_management(
    skills_manager,
    create_skill,
    add_skill,
    from_readme,
    ai,
    provider,
    force,
    strategy,
    output_dir,
    create_rules_flag,
    remove_skill,
    list_skills,
    verbose,
):
    """Handle create-skill / remove-skill / list-skills early-exit actions.

    Returns True if the caller should sys.exit(0) immediately after, False otherwise.
    """
    import shutil

    if create_skill or add_skill:
        skill_name = create_skill or add_skill
        try:
            path = skills_manager.create_skill(
                skill_name,
                from_readme=from_readme,
                project_path=str(skills_manager.project_path),
                use_ai=ai,
                provider=provider or "groq",
                force=force,
                strategy=strategy if ai else None,
            )
            click.echo(f"✨ Created new skill '{path.name}' in {path}")
            click.echo("🔄 Updating agent cache...")
            skills_manager.save_triggers_json(output_dir)
            click.echo("✅ auto-triggers.json refreshed!")
        except Exception as e:
            click.echo(f"❌ Failed to create skill: {e}", err=True)
            sys.exit(1)
        if not create_rules_flag:
            sys.exit(0)

    if remove_skill:
        target = (skills_manager.learned_path / remove_skill).resolve()
        try:
            target.relative_to(skills_manager.learned_path.resolve())
        except ValueError:
            click.echo(f"❌ Invalid skill path: {remove_skill}", err=True)
            sys.exit(1)
        if target.exists():
            shutil.rmtree(target)
            click.echo(f"🗑️ Removed skill '{remove_skill}'")
        else:
            click.echo(f"❌ Skill '{remove_skill}' not found in learned skills.", err=True)
            sys.exit(1)
        sys.exit(0)

    if list_skills:
        skills = skills_manager.list_skills()
        display_groups = {"project": [], "learned": [], "builtin": []}
        for name, data in skills.items():
            stype = data["type"]
            if stype in display_groups:
                display_groups[stype].append(name)
        total = len(skills)
        click.echo(f"\nAvailable Skills ({total}):")
        if display_groups["project"]:
            click.echo(f"\n📁 Project Overrides ({len(display_groups['project'])}):")
            for s in sorted(display_groups["project"]):
                click.echo(f"  - {s} (Local)")
        if display_groups["learned"]:
            click.echo(f"\n🧠 Learned Skills (Global & Local) ({len(display_groups['learned'])}):")
            for s in sorted(display_groups["learned"]):
                click.echo(f"  - {s}")
        if display_groups["builtin"]:
            click.echo(f"\n🛠️  Global Builtin ({len(display_groups['builtin'])}):")
            for s in sorted(display_groups["builtin"]):
                click.echo(f"  - {s}")
        if not total:
            click.echo("  No skills found.")
        sys.exit(0)


def _run_create_rules(project_path, readme_path, project_name, project_data, enhanced_context, output_dir,
                      rules_quality_threshold, verbose, generated_files):
    """Run the --create-rules CoworkRulesCreator block."""
    try:
        from generator.rules_creator import CoworkRulesCreator

        if verbose:
            click.echo("\n🎯 Cowork Rules Creator...")

        if readme_path and readme_path.exists():
            readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
        else:
            readme_text = f"# {project_name}\n\nProject analysis in progress..."

        tech_stack_arg = project_data.get("tech_stack") or None
        creator = CoworkRulesCreator(project_path)
        content, metadata, quality = creator.create_rules(
            readme_text,
            tech_stack=tech_stack_arg,
            enhanced_context=enhanced_context,
        )

        if verbose:
            click.echo(f"   Tech Stack: {', '.join(metadata.tech_stack) or 'none'}")
            click.echo(f"   Project Type: {metadata.project_type}")
            click.echo(f"   Quality Score: {quality.score:.1f}/100")

        if quality.score < rules_quality_threshold:
            click.echo(
                f"   ⚠️  Quality score {quality.score:.1f} below threshold {rules_quality_threshold}",
                err=True,
            )

        cowork_rules_file = creator.export_to_file(content, metadata, output_dir)
        generated_files.append(cowork_rules_file)
        if verbose:
            click.echo(f"   ✅ Cowork rules.md saved: {cowork_rules_file}")
    except Exception as e:
        click.echo(f"   ⚠️  Cowork rules generation failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()


def setup_orchestrator(config):
    """Initialize and configure SkillOrchestrator."""
    from generator.orchestrator import SkillOrchestrator
    from generator.sources.builtin import BuiltinSkillsSource
    from generator.sources.learned import LearnedSkillsSource

    orchestrator = SkillOrchestrator(config)
    orchestrator.register_source(BuiltinSkillsSource(config))
    orchestrator.register_source(LearnedSkillsSource(config))
    return orchestrator


@click.command(name="analyze")
@click.argument("project_path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--commit/--no-commit", default=True, help="Auto-commit to git")
@click.option("--interactive", "-i", is_flag=True, help="Interactive prompts")
@click.option("--verbose/--quiet", default=False, help="Verbose output (version banner, provider info)")
@click.option("--export-json", is_flag=True, help="Export skills as JSON")
@click.option("--export-yaml", is_flag=True, help="Export skills as YAML")
@click.option(
    "--save-learned",
    is_flag=True,
    help="Save newly generated skills to learned library",
)
@click.option("--include-pack", multiple=True, help="Include external skill pack (name or path)")
@click.option(
    "--external-packs-dir",
    type=click.Path(exists=True, file_okay=False),
    help="Directory containing external packs",
)
@click.option("--list-skills", is_flag=True, help="List all available skills from all sources")
@click.option("--create-skill", help="Create a new learned skill with the given name")
@click.option(
    "--from-readme",
    type=click.Path(exists=True, dir_okay=False),
    help="Use README as context for new skill",
)
@click.option(
    "--ai",
    is_flag=True,
    help="Use AI to generate skill content (requires an API key — any supported provider)",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False),
    default=".clinerules",
    help="Output directory (default: .clinerules)",
)
@click.option("--with-skills", is_flag=True, default=True, help="Include skills in output")
@click.option(
    "--auto-generate-skills",
    is_flag=True,
    help="Auto-detect and generate skills (requires --ai)",
)
@click.option("--api-key", help="API Key (overrides env var)")
@click.option(
    "--constitution",
    is_flag=True,
    help="Generate constitution.md with project-specific coding principles",
)
@click.option("--merge", is_flag=True, help="Preserve existing skill files, only add new ones")
@click.option(
    "--mode",
    type=click.Choice(["manual", "ai", "constitution"]),
    default=None,
    help="Explicit mode (manual=no AI, ai=auto-generate+AI, constitution=adds constitution.md)",
)
@click.option(
    "--incremental",
    is_flag=True,
    help="Only regenerate changed sections (skip if nothing changed)",
)
@click.option("--ide", help="Register rules with IDE (antigravity, cline, cursor, vscode)")
@click.option(
    "--provider",
    type=click.Choice(["gemini", "groq", "anthropic", "openai"]),
    default=None,
    help="AI Provider (gemini, groq, anthropic, openai). Auto-detected from env vars if omitted.",
)
@click.option(
    "--strategy",
    default="auto",
    show_default=True,
    help=(
        "Router strategy: auto (smart fallback), speed, quality, "
        "or provider:<name> (e.g. provider:anthropic)"
    ),
)
@click.option("--add-skill", help="Add a skill (alias for create-skill)")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force overwrite if skill already exists (default: skip existing)",
)
@click.option("--remove-skill", help="Remove a learned skill")
@click.option(
    "--quality-check",
    is_flag=True,
    help="Analyze quality of generated .clinerules files",
)
@click.option(
    "--eval-opik",
    is_flag=True,
    help="Run Comet Opik evaluation (requires OPIK_API_KEY)",
)
@click.option(
    "--auto-fix",
    is_flag=True,
    help="Automatically fix low-quality files (requires --quality-check)",
)
@click.option(
    "--max-iterations",
    type=int,
    default=3,
    help="Max improvement iterations for auto-fix (default: 3)",
)
@click.option(
    "--generate-index",
    is_flag=True,
    help="Auto-generate skills/index.md from available skills",
)
@click.option(
    "--create-rules",
    "create_rules_flag",
    is_flag=True,
    help="Generate Cowork-quality rules.md (overrides default rules generation)",
)
@click.option(
    "--rules-quality-threshold",
    type=int,
    default=85,
    help="Minimum quality score for --create-rules (default: 85)",
)
@click.option(
    "--skills-dir",
    type=click.Path(file_okay=False),
    help="Custom skills directory (default: ./skills)",
)
def analyze(
    project_path,
    commit,
    interactive,
    verbose,
    export_json,
    export_yaml,
    save_learned,
    include_pack,
    external_packs_dir,
    list_skills,
    create_skill,
    from_readme,
    ai,
    output,
    with_skills,
    auto_generate_skills,
    api_key,
    constitution,
    merge,
    mode,
    incremental,
    ide,
    provider,
    add_skill,
    force,
    remove_skill,
    quality_check,
    eval_opik,
    auto_fix,
    max_iterations,
    generate_index,
    create_rules_flag,
    rules_quality_threshold,
    skills_dir,
    strategy,
):
    """Analyze project and generate rules.md and skills.md from README.md"""
    project_path = Path(project_path).resolve()
    cleanup_awesome_skills()

    # Invoke with default skills_dir=None to allow SkillDiscovery to use its default (.clinerules/skills)
    # skills_dir = skills_dir or "skills"

    # Initialize Skills Manager with project context
    skills_manager = SkillsManager(project_path=project_path, skills_dir=skills_dir)

    # Handle --generate-index flag (standalone action)
    if generate_index:
        try:
            index_path = skills_manager.generate_perfect_index()
            click.echo(f"✅ Perfect index.md generated at: {index_path}")
            sys.exit(0)
        except Exception as e:
            click.echo(f"❌ Failed to generate index.md: {e}", err=True)
            sys.exit(1)

    # Handle --mode shortcut
    if mode == "ai":
        auto_generate_skills = True
        ai = True
    elif mode == "constitution":
        constitution = True
    # mode == 'manual' changes nothing (no AI)

    # When provider is explicitly set (implying AI intent) and mode isn't
    # manual, auto-enable enhanced features so a fresh project gets
    # constitution.md + clinerules.yaml + project-specific learned skills.
    if provider is not None and mode != "manual":
        auto_generate_skills = True
        ai = True
        constitution = True

    # Create output directory structure
    output_dir = project_path / output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup .clinerules/skills structure (symlinks/copies)
    try:
        skills_manager.setup_project_structure()
        if verbose:
            click.echo("✅ Skills structure initialized (Global -> Project)")
    except Exception as e:
        if verbose:
            click.echo(f"⚠️  Skills structure setup warning: {e}")
        # Non-fatal, might just be symlink issues, meaningful error printed inside manager

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
        click.echo(f"Project Rules Generator v{__version__}")
        click.echo(f"Target: {project_path}")
    else:
        setup_logging(verbose=False)

    # Auto-detect provider and set environment variable
    provider = detect_provider(provider, api_key)
    if verbose:
        click.echo(f"Auto-detected provider: {provider}")
    set_api_key_env(provider, api_key)
    if api_key and verbose:
        click.echo(f"Using API key from --api-key flag for {provider}")

    try:
        # Load config
        config = load_config()

        # Override config with CLI flags
        if save_learned:
            # Ensure structure exists
            if "skill_sources" not in config:
                config["skill_sources"] = {}
            if "learned" not in config["skill_sources"]:
                config["skill_sources"]["learned"] = {}
            config["skill_sources"]["learned"]["auto_save"] = True

        # Skill Management (CLI Flags) — early-exit paths
        _handle_skill_management(
            skills_manager=skills_manager,
            create_skill=create_skill,
            add_skill=add_skill,
            from_readme=from_readme,
            ai=ai,
            provider=provider,
            force=force,
            strategy=strategy,
            output_dir=output_dir,
            create_rules_flag=create_rules_flag,
            remove_skill=remove_skill,
            list_skills=list_skills,
            verbose=verbose,
        )

        # Load External Packs
        if include_pack or (config.get("packs") and config["packs"].get("enabled")):
            load_external_packs(
                include_packs=include_pack,
                config_packs=config.get("packs"),
                external_packs_dir=external_packs_dir,
                verbose=verbose,
            )

        # Find README
        from generator.utils.readme_bridge import find_readme

        readme_path = find_readme(project_path)

        # Interactive README Generation
        from generator.interactive import create_readme_interactive, show_generated_files
        from generator.readme_generator import is_readme_minimal

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
                    # Need context for generation
                    from generator.project_analyzer import ProjectAnalyzer
                    from generator.readme_generator import generate_readme_template, generate_readme_with_llm

                    analyzer = ProjectAnalyzer(project_path)
                    context = analyzer.analyze()

                    if ai:
                        click.echo("🤖 Generating README with AI...\\n")
                        content = generate_readme_with_llm(user_input_data, context)
                    else:
                        content = generate_readme_template(user_input_data, context)

                    if not readme_path:
                        readme_path = project_path / "README.md"

                    readme_path.write_text(content, encoding="utf-8")
                    click.echo(f"✅ README.md created/updated and saved to {readme_path}\\n")

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
                "name": project_path.name,
                "tech_stack": sorted(list(set(sum(context["tech_stack"].values(), [])))),
                "features": [],
                "description": "No README provided.",
                "raw_name": project_path.name,
                "readme_path": None,
            }
        project_name = project_data["name"]

        if verbose:
            click.echo("\\nDetected:")
            click.echo(f"   Name: {project_name}")
            click.echo(
                f"   Tech: {', '.join(project_data['tech_stack']) if project_data['tech_stack'] else 'None detected'}"
            )
            click.echo(f"   Features: {len(project_data['features'])} found")

        # Interactive mode confirmation for rules generation
        if interactive:
            from rich.prompt import Confirm

            from generator.utils import flush_input

            # Fixed Bug #1: Ensure single prompt
            flush_input()
            if not Confirm.ask(
                f"Continue generating .clinerules for [bold]{project_name}[/bold]?",
                default=True,
            ):
                click.echo("Aborted.")
                sys.exit(0)

        # Generate files with progress bar if available
        if verbose:
            click.echo("\\nGenerating files...")

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
                constitution_content = generate_constitution(project_name, enhanced_context, project_path=project_path)
                constitution_path = output_dir / "constitution.md"
                constitution_path.write_text(constitution_content, encoding="utf-8")
                generated_files.append(constitution_path)
                if verbose:
                    click.echo("   Generated constitution.md")
            elif constitution and not enhanced_context:
                if verbose:
                    click.echo("   Skipping constitution (enhanced analysis unavailable)")

            pbar.set_description("Generating Rules")
            rules_content = generate_rules(project_data, config, enhanced_context=enhanced_context)
            pbar.update(1)

            pbar.set_description("Processing Skills")
            # Enhanced auto-generate skills using new Phase 1-4 modules
            enhanced_selected_skills = set()
            if auto_generate_skills:
                try:
                    # Use already-extracted enhanced_context, or extract if missing
                    if enhanced_context is None:
                        enhanced_parser = EnhancedProjectParser(project_path)
                        enhanced_context = enhanced_parser.extract_full_context()

                    detected_tech = enhanced_context.get("metadata", {}).get("tech_stack", [])
                    project_type = enhanced_context.get("metadata", {}).get("project_type", "unknown")

                    if verbose:
                        click.echo("\\n   Enhanced Analysis:")
                        click.echo(f"   Project Type: {project_type}")
                        click.echo(f"   Tech Stack: {', '.join(detected_tech)}")
                        dep_count = len(enhanced_context.get("dependencies", {}).get("python", []))
                        dep_count += len(enhanced_context.get("dependencies", {}).get("node", []))
                        click.echo(f"   Dependencies: {dep_count} parsed")
                        test_info = enhanced_context.get("test_patterns", {})
                        if test_info.get("framework"):
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
                        llm_auth_failed = False

                        for skill_ref in sorted(enhanced_selected_skills):
                            if not skill_ref.startswith("learned/"):
                                continue

                            # Fail fast: stop LLM attempts after auth failure
                            if llm_auth_failed:
                                continue

                            # Check if skill already exists
                            existing_path = SkillPathManager.get_skill_path(skill_ref)
                            if existing_path and existing_path.exists():
                                continue

                            # Extract code examples for this skill
                            skill_topic = skill_ref.split("/")[-1]
                            examples = extractor.extract_examples_for_skill(project_path, skill_topic, detected_tech)

                            # Build enhanced prompt
                            prompt = build_skill_prompt(
                                skill_topic=skill_topic,
                                project_name=project_name,
                                context=enhanced_context,
                                code_examples=examples,
                                detected_patterns=enhanced_context.get("structure", {}).get("patterns", []),
                                project_path=project_path,
                            )

                            try:
                                from generator.llm_skill_generator import LLMSkillGenerator

                                current_provider = provider
                                llm_gen = LLMSkillGenerator(provider=current_provider)
                                skill_content = llm_gen.generate_content(prompt, max_tokens=2000)

                                # Save using SkillPathManager, then invalidate
                                # SkillDiscovery cache so the new file is visible.
                                parts = skill_ref.split("/")
                                category = parts[1] if len(parts) >= 3 else "general"
                                SkillPathManager.save_learned_skill(
                                    {"name": skill_topic, "content": skill_content},
                                    category,
                                )
                                skills_manager.discovery.invalidate_cache()
                                click.echo(f"   💾 Generated: {skill_ref}")
                            except Exception as e:
                                err_str = str(e)
                                click.echo(f"   ⚠️  Failed to generate {skill_ref}: {e}")
                                # Fail fast on auth errors — no point retrying
                                if (
                                    "invalid_api_key" in err_str
                                    or "401" in err_str
                                    or "authentication" in err_str.lower()
                                ):
                                    click.echo("   ❌ API key invalid — skipping remaining LLM generations")
                                    llm_auth_failed = True

                except Exception as e:
                    click.echo(f"Warning: Enhanced auto-generation failed: {e}")
                    if verbose:
                        import traceback

                        traceback.print_exc()

            # Extract Triggers
            triggers_dict = {}
            if with_skills:
                triggers_dict = skills_manager.extract_all_triggers()
                # Save triggers for AgentExecutor
                skills_manager.save_triggers_json(output_dir)
            pbar.update(1)

            pbar.set_description("Unified Export (.clinerules/)")
            # Build Unified Content
            unified_content = rules_content + "\\n\\n# 🧠 Agent Skills\\n\\n"

            if triggers_dict:
                unified_content += "## Active Skill Triggers\\n"
                for skill, phrases in triggers_dict.items():
                    # We don't have category easily available in the dict, but that's fine for now
                    unified_content += f"- **{skill}**: {', '.join(phrases)}\\n"
                unified_content += "\\n"

                # Embed full skill content (optional, but requested 'Unified')
                # For .clinerules, having the full context is good.
                unified_content += "## Skill Definitions\\n"
                all_skills = skills_manager.get_all_skills_content()
                for skill_name in triggers_dict:
                    # Find which category this skill belongs to
                    found_content = None
                    for category in ["project", "learned", "builtin"]:
                        if category in all_skills and skill_name in all_skills[category]:
                            found_content = all_skills[category][skill_name]["content"]
                            break

                    if found_content:
                        unified_content += f"\\n### Skill: {skill_name}\\n{found_content}\\n"

            # If enhanced matching was done, also generate lightweight clinerules
            if enhanced_selected_skills:
                lightweight_yaml = generate_clinerules(
                    project_name,
                    enhanced_selected_skills,
                    enhanced_context,
                    output_dir=output_dir,
                )
                # Append as YAML reference block
                unified_content += f"\\n\\n<!-- Lightweight Skill References\\n{lightweight_yaml}-->\\n"

                # Save standalone lightweight clinerules.yaml inside output dir
                lightweight_path = output_dir / "clinerules.yaml"
                lightweight_path.write_text(lightweight_yaml, encoding="utf-8")
                generated_files.append(lightweight_path)
                if verbose:
                    click.echo(f"   Generated clinerules.yaml ({len(enhanced_selected_skills)} skills)")

                # Generate project-specific learned skills from README
                # (runs BEFORE stub creation so project context takes priority)
                if readme_path and readme_path.exists():
                    readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
                    project_tech = project_data.get("tech_stack", [])

                    # Cross-project reuse report
                    if verbose:
                        reuse_map = skills_manager.check_global_skill_reuse(project_tech)
                        if reuse_map:
                            click.echo("\n   Global skill reuse check:")
                            for skill_name, action in sorted(reuse_map.items()):
                                icon = {"reuse": "♻️ ", "adapt": "🔧", "create": "✨"}.get(action, "  ")
                                click.echo(f"     {icon} {skill_name}: {action}")

                    generated_skills = skills_manager.generate_from_readme(
                        readme_content=readme_text,
                        tech_stack=project_tech,
                        output_dir=output_dir,
                        project_name=project_name,
                        project_path=project_path,
                    )
                    if generated_skills and verbose:
                        click.echo(f"   Generated {len(generated_skills)} project-specific skills:")
                        for s in generated_skills:
                            click.echo(f"     - {s}")

                # Copy skill files into output_dir/skills/
                import shutil

                existing_skill_files = set()
                if merge and (output_dir / "skills").exists():
                    # Collect existing skill files for merge logic
                    for subdir in ("builtin", "learned"):
                        skill_subdir = output_dir / "skills" / subdir
                        if skill_subdir.exists():
                            for f in skill_subdir.iterdir():
                                if f.is_file():
                                    existing_skill_files.add(f.name)

                for skill_ref in sorted(enhanced_selected_skills):
                    skill_path = SkillPathManager.get_skill_path(skill_ref)
                    ref_name = skill_ref.split("/")[-1]
                    dest_name = f"{ref_name}.md" if not ref_name.endswith(".md") else ref_name
                    if skill_ref.startswith("builtin/"):
                        dest = output_dir / "skills" / "builtin" / dest_name
                    elif skill_ref.startswith("learned/"):
                        dest = output_dir / "skills" / "learned" / dest_name
                    else:
                        continue

                    if skill_path and skill_path.exists():
                        shutil.copy2(skill_path, dest)
                    elif not dest.exists():
                        # Materialize a context-aware stub for referenced skills with no file
                        parts = skill_ref.split("/")
                        category = parts[1] if len(parts) >= 3 else "general"
                        title = ref_name.replace("-", " ").title()

                        # Extract README context for this skill's tech category
                        stub_context_lines = []
                        if readme_path and readme_path.exists():
                            stub_context_lines = skills_manager._extract_tech_context(
                                category,
                                readme_path.read_text(encoding="utf-8", errors="replace"),
                            )

                        if stub_context_lines:
                            # Build a context-aware stub
                            purpose = skills_manager._summarize_purpose(category, stub_context_lines, project_name)
                            guidelines = skills_manager._build_guidelines(category, stub_context_lines)
                            stub = (
                                f"# {title}\\n\\n"
                                f"**Project:** {project_name}\\n"
                                f"**Category:** {category}\\n\\n"
                                f"## Purpose\\n\\n{purpose}\\n\\n"
                                f"## Auto-Trigger\\n\\n"
                                f"- Working with {category} integration code\\n"
                                f"- Editing files that import or configure {category}\\n\\n"
                                f"## Guidelines\\n\\n{guidelines}\\n\\n"
                                f"## Project Context (from README)\\n\\n"
                            )
                            for ctx_line in stub_context_lines[:5]:
                                stub += f"> {ctx_line}\\n"
                        else:
                            # Minimal stub — no context available
                            stub = (
                                f"# {title}\\n\\n"
                                f"**Project:** {project_name}\\n"
                                f"**Category:** {category}\\n\\n"
                                f"## Purpose\\n\\n"
                                f"Integration patterns for {ref_name.replace('-', ' ')} in {project_name}.\\n\\n"
                                f"## Auto-Trigger\\n\\n"
                                f"- Working with {category} code\\n\\n"
                                f"## Guidelines\\n\\n"
                                f"- Refer to project README for {category} usage patterns\\n"
                                f"- Handle errors with proper retries and fallbacks\\n"
                            )
                        dest.write_text(stub, encoding="utf-8")
                        if verbose:
                            label = "📝 Stub+" if stub_context_lines else "📄 Stub"
                            click.echo(f"   {label}: {dest_name}")

            # Write rules.md into output directory (with incremental merge if applicable)
            rules_path = output_dir / "rules.md"
            if inc_analyzer and rules_path.exists():
                existing_rules = rules_path.read_text(encoding="utf-8")
                unified_content = IncrementalAnalyzer.merge_rules(existing_rules, unified_content, changed_sections)
            save_markdown(rules_path, unified_content)
            generated_files.append(rules_path)

            # Generate rules.json alongside rules.md
            from generator.rules_generator import rules_to_json

            rules_json_path = output_dir / "rules.json"
            rules_json_path.write_text(rules_to_json(unified_content), encoding="utf-8")

            # [New] Save Auto-Triggers for Agent
            if verbose:
                click.echo("Generating auto-triggers...")
            skills_manager.save_triggers_json(output_dir)
            generated_files.append(rules_json_path)
            if verbose:
                click.echo("   Generated rules.json")
            pbar.update(1)

            # Orchestrated skill generation
            pbar.set_description("Saving Skill Artifacts")
            # Initialize Orchestrator
            from generator.renderers import get_renderer
            from generator.sources.learned import LearnedSkillsSource
            from generator.types import SkillFile

            orchestrator = setup_orchestrator(config)

            # Run orchestration
            skills = orchestrator.orchestrate(project_data, str(project_path))

            # Save learned skills if requested
            if save_learned:
                learned_source = next(
                    (s for s in orchestrator.sources if isinstance(s, LearnedSkillsSource)),
                    None,
                )
                if learned_source:
                    for skill in skills:
                        learned_source.save_skill(skill)

            # Create SkillFile wrapper
            from generator.analyzers.project_type_detector import detect_project_type_from_data

            type_info = detect_project_type_from_data(project_data, str(project_path))

            skill_file = SkillFile(
                project_name=project_name,
                project_type=type_info["primary_type"],
                skills=skills,
                confidence=type_info["confidence"],
                tech_stack=project_data.get("tech_stack", []),
                description=project_data.get("description", ""),
            )

            # Render Markdown skills index
            skills_content = get_renderer("markdown").render(skill_file)

            # Write skills index into output directory
            skills_index_path = output_dir / "skills" / "index.md"
            save_markdown(skills_index_path, skills_content)
            generated_files.append(skills_index_path)

            # Handle exports (into output_dir/skills/)
            if export_json:
                json_content = get_renderer("json").render(skill_file)
                json_path = output_dir / "skills" / "index.json"
                json_path.write_text(json_content, encoding="utf-8")
                generated_files.append(json_path)

            if export_yaml:
                yaml_content = get_renderer("yaml").render(skill_file)
                yaml_path = output_dir / "skills" / "index.yaml"
                yaml_path.write_text(yaml_content, encoding="utf-8")
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
            skills_stats = {"learned": 0, "builtin": 0, "generated": 0}
            for s in skills:
                if hasattr(s, "source"):
                    if s.source == "learned":
                        skills_stats["learned"] += 1
                    elif s.source == "builtin":
                        skills_stats["builtin"] += 1
                    elif s.source == "generated":
                        skills_stats["generated"] += 1
                    else:
                        skills_stats["generated"] += 1  # Default

            show_generated_files(generated_files, skills_stats)
        else:
            click.echo("\\nGenerated files:")
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
                    click.echo("\\nWARNING: Not a git repository, skipping commit")
            else:
                commit_msg = config.get("git", {}).get("commit_message", "Auto-generated rules and skills")
                user_name = config.get("git", {}).get("commit_user_name")
                user_email = config.get("git", {}).get("commit_user_email")

                try:
                    result = commit_files(generated_files, commit_msg, project_path, user_name, user_email)
                    click.echo("\\nCommitted to git")
                    if "nothing to commit" in result.lower():
                        click.echo("   (or files already tracked)")
                except Exception as e:
                    click.echo(f"\\nWARNING: Git commit failed: {e}")
                    click.echo("   Files were generated, you can commit manually")

        # Save incremental cache
        if inc_analyzer:
            inc_analyzer.save_hash(inc_analyzer.compute_project_hash())
            if verbose:
                click.echo("   Saved incremental cache")

        # Quality Check (Phase 1 - Analyzer Agent)
        if quality_check or eval_opik:
            run_quality_check(
                output_dir=output_dir,
                project_path=project_path,
                provider=provider,
                api_key=api_key,
                eval_opik=eval_opik,
                auto_fix=auto_fix,
                verbose=verbose,
            )

        # Cowork Rules Creator integration (delegation)
        if create_rules_flag:
            _run_create_rules(
                project_path=project_path,
                readme_path=readme_path,
                project_name=project_name,
                project_data=project_data,
                enhanced_context=enhanced_context,
                output_dir=output_dir,
                rules_quality_threshold=rules_quality_threshold,
                verbose=verbose,
                generated_files=generated_files,
            )

        click.echo("\\nDone!")

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
        click.echo(f"❌ Unexpected Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    analyze()

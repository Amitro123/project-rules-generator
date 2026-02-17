import click
from pathlib import Path
from refactor.analyze_cmd import analyze
from refactor.create_skills_cmd import create_skills
from refactor.create_rules_cmd import create_rules

class GuidedFlow:
    def __init__(self, project_path: Path):
        self.project_path = project_path

    def run(self):
        """Run the interactive guided flow."""
        click.echo("🧭 Starting Guided Flow...")
        
        ctx = click.get_current_context()
        
        # 1. Rules Generation
        if click.confirm("Do you want to generate Global Rules & Tasks? (Recommended)", default=True):
            click.echo("   Running analyze --full-flow...")
            ctx.invoke(analyze, project_path=str(self.project_path), full_flow=True)
        else:
            if click.confirm("   Run basic local analysis instead?", default=True):
                ctx.invoke(analyze, project_path=str(self.project_path))

        # 2. Cowork Rules
        if click.confirm("\nDo you want to generate high-quality Cowork Rules?", default=True):
             tech = click.prompt("   Enter tech stack (comma-separated, e.g. fastapi,react)", default="")
             ctx.invoke(create_rules, project_path=str(self.project_path), tech=tech if tech else None)

        # 3. Skills
        if click.confirm("\nDo you want to generate custom skills?", default=True):
            use_ai = click.confirm("   Use AI for better skills? (Requires API Key)", default=False)
            ctx.invoke(create_skills, project_path=str(self.project_path), ai=use_ai, auto_fix=True)

        click.echo("\n✨ Guided Flow Complete!")

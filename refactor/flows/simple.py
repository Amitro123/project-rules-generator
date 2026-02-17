import click
from pathlib import Path
from refactor.analyze_cmd import analyze

class SimpleFlow:
    def __init__(self, project_path: Path):
        self.project_path = project_path

    def run(self):
        """Run the simple analysis flow."""
        click.echo("🚀 Starting Simple Flow...")
        
        # 1. Run basic analysis (no AI, no full flow)
        ctx = click.get_current_context()
        ctx.invoke(analyze, project_path=str(self.project_path))
        
        click.echo("\n✅ Simple Analysis Complete!")
        click.echo("\nNext Steps:")
        click.echo("1. Review .clinerules/rules.md")
        click.echo("2. Run 'prg create-skills .' to add skills")
        click.echo("3. Run 'prg status' to see project status")

import click
from pathlib import Path
from refactor.autopilot_cmd import autopilot

class AutoFlow:
    def __init__(self, project_path: Path):
        self.project_path = project_path

    def run(self, discovery_only: bool = False):
        """Run the autopilot flow."""
        click.echo("🤖 Starting Autopilot Flow...")
        
        ctx = click.get_current_context()
        # Delegate to existing autopilot command
        ctx.invoke(autopilot, project_path=str(self.project_path), discovery_only=discovery_only)


"""
CLI command for managing global configuration.
Stores config in ~/.project-rules-generator/config.yaml
"""

import click
import yaml
from pathlib import Path
from typing import Dict, Any

CONFIG_DIR = Path.home() / ".project-rules-generator"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

def load_config() -> Dict[str, Any]:
    """Load global config."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def save_config(config: Dict[str, Any]):
    """Save global config."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        yaml.dump(config, f)

@click.group("config")
def config_cmd():
    """Manage global configuration."""
    pass

@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def set_config(key: str, value: str):
    """Set a configuration value (e.g. llm.provider groq)."""
    config = load_config()
    
    # Handle nested keys (e.g. llm.provider)
    parts = key.split(".")
    current = config
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
        if not isinstance(current, dict):
             click.echo(f"Error: Key conflict at {part}", err=True)
             return

    current[parts[-1]] = value
    save_config(config)
    click.echo(f"✅ Set {key} = {value}")

@config_cmd.command("get")
@click.argument("key")
def get_config(key: str):
    """Get a configuration value."""
    config = load_config()
    parts = key.split(".")
    current = config
    
    try:
        for part in parts:
            current = current[part]
        click.echo(current)
    except (KeyError, TypeError):
        click.echo(f"Key '{key}' not set.")

@config_cmd.command("list")
def list_config():
    """List all configuration."""
    if not CONFIG_FILE.exists():
        click.echo("No configuration file found.")
        return
        
    click.echo(f"Config file: {CONFIG_FILE}")
    click.echo(CONFIG_FILE.read_text(encoding="utf-8"))

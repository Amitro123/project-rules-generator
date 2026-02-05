from pathlib import Path
from typing import List, Optional, Dict, Any
import click
from .types import SkillPack
from .importers import get_importer_for_path

def load_external_packs(
    include_packs: List[str],
    config_packs: Optional[Dict[str, Any]] = None,
    external_packs_dir: Optional[str] = None,
    verbose: bool = False
) -> List[SkillPack]:
    """
    Load external skill packs from CLI arguments and config.
    """
    external_packs = []

    # Combine CLI packs and config packs
    packs_to_load = list(include_packs)
    if config_packs and config_packs.get('sources'):
         packs_to_load.extend(config_packs['sources'])

    if not packs_to_load:
        return external_packs

    if verbose:
        click.echo("\nLoading external packs...")

    # Resolver logic
    for pack_ref in packs_to_load:
        pack_path = None

        # Check if it's a known alias or local path
        # 1. Try as direct path
        path_obj = Path(pack_ref)
        if path_obj.exists():
            pack_path = path_obj
        # 2. Try in external_packs_dir if provided
        elif external_packs_dir:
            p = Path(external_packs_dir) / pack_ref
            if p.exists():
                pack_path = p

        # Load pack
        if pack_path:
            importer = get_importer_for_path(pack_path)

            try:
                pack = importer.import_skills(pack_path)
                if pack and pack.skills:
                    external_packs.append(pack)
                    if verbose:
                        click.echo(f"   + Loaded {pack.name} ({len(pack.skills)} skills)")
                else:
                     if verbose:
                        click.echo(f"   ! Warn: No skills found in {pack_ref}")
            except Exception as e:
                click.echo(f"   x Failed to load {pack_ref}: {e}", err=True)
        else:
            if verbose:
                click.echo(f"   ! Warn: Pack not found: {pack_ref}")

    return external_packs

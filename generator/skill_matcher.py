from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import yaml
from .types import Skill

logger = logging.getLogger(__name__)

class SkillMatcher:
    '''
    Simplified 2-tier skill matching:
    1. Learned (user history) - CHECK FIRST
    2. Builtin (universal) - CHECK SECOND
    3. Generate new (AI) - FALLBACK
    '''

    def __init__(self, learned_dir: Path, builtin_dir: Path):
        self.learned_dir = learned_dir
        self.builtin_dir = builtin_dir
        # Ensure directories exist (at least conceptually)
        
    def find_skill(self, skill_name: str, project_context: Dict[str, Any]) -> Optional[Skill]:
        '''
        Find best matching skill with 2-tier priority.
        Returns None if skill needs to be generated.
        '''

        # Tier 1: Check learned skills (user's history - HIGHEST PRIORITY)
        learned = self._check_learned(skill_name, project_context)
        if learned:
            logger.info(f"✅ LEARNED: {skill_name} (from your previous projects)")
            return learned

        # Tier 2: Check builtin skills (universal patterns - MEDIUM PRIORITY)
        builtin = self._check_builtin(skill_name, project_context)
        if builtin:
            logger.info(f"✅ BUILTIN: {skill_name} (universal pattern)")
            return builtin

        # Tier 3: Need to generate (will be saved to learned)
        logger.info(f"🤖 GENERATE: {skill_name} (will be saved to learned)")
        return None

    def _check_learned(self, skill_name: str, context: Dict[str, Any]) -> Optional[Skill]:
        '''Check user's learned skills from previous projects'''
        # 1. Exact match (YAML or MD in directory)
        # Check standard locations
        
        # Check YAML
        yaml_path = self.learned_dir / f"{skill_name}.yaml"
        if yaml_path.exists():
            skill = self._load_skill(yaml_path)
            if skill and self._is_relevant(skill, context):
                skill.source = "learned"
                return skill

        # Check Directory with SKILL.md
        dir_path = self.learned_dir / skill_name / "SKILL.md"
        if dir_path.exists():
             skill = self._load_skill_md(dir_path)
             if skill and self._is_relevant(skill, context):
                skill.source = "learned"
                return skill

        # 2. Versioned matches (e.g., fastapi-auth-v3.yaml)
        # TODO: simpler glob for now
        return None

    def _check_builtin(self, skill_name: str, context: Dict[str, Any]) -> Optional[Skill]:
        '''Check builtin universal skills'''
        
        # Search recursively or flat? Builtin might be organized by category.
        # Let's try flat match first, then recursive.
        
        # Recursive search for exact name
        for path in self.builtin_dir.rglob(f"{skill_name}.*"):
             if path.suffix in ['.yaml', '.yml']:
                 skill = self._load_skill(path)
                 if skill:
                     skill.source = "builtin"
                     return skill
             elif path.name == "SKILL.md" and path.parent.name == skill_name:
                 skill = self._load_skill_md(path)
                 if skill:
                     skill.source = "builtin"
                     return skill
        
        return None

    def _is_relevant(self, skill: Skill, context: Dict[str, Any]) -> bool:
        '''
        Validate if skill matches current project context.
        For now, assume relevant if found by name.
        '''
        return True

    def _load_skill(self, path: Path) -> Optional[Skill]:
        '''Load and parse YAML skill file'''
        try:
            with open(path, encoding='utf-8') as f:
                data = yaml.safe_load(f)

            return Skill(
                name=data.get('name', path.stem),
                description=data.get('description', ''),
                content=data.get('content', ''),
                source="unknown", # set by caller
                tools=data.get('tools', []),
                auto_triggers=data.get('auto_triggers', [])
            )

        except Exception as e:
            logger.warning(f"Failed to load {path.name}: {e}")
            return None

    def _load_skill_md(self, path: Path) -> Optional[Skill]:
        '''Load and parse Markdown skill file'''
        try:
            content = path.read_text(encoding='utf-8')
            # Extract metadata if possible, else just use content
            import re
            parts = re.split(r'^---\s*$', content, maxsplit=2, flags=re.MULTILINE)
            metadata = {}
            body = content
            if len(parts) >= 3:
                 try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2]
                 except: pass
            
            return Skill(
                name=metadata.get('name', path.parent.name),
                description=metadata.get('description', ''),
                content=body.strip(),
                source="unknown",
                tools=metadata.get('tools', [])
            )
        except Exception:
            return None

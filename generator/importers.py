import yaml
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from .types import Skill, SkillPack

class SkillImporter:
    def import_skills(self, source_path: Path) -> SkillPack:
        raise NotImplementedError

class AgentRulesImporter(SkillImporter):
    """Imports skills from .mdc/.md files with YAML frontmatter (steipete/agent-rules style)."""
    
    def import_skills(self, source_path: Path) -> SkillPack:
        skills = []
        pack_name = source_path.name
        
        if source_path.is_file():
            files = [source_path]
        else:
            # Look for .mdc and .md files
            files = list(source_path.glob("**/*.mdc")) + list(source_path.glob("**/*.md"))
            
        for file_path in files:
            if file_path.name.lower() == "readme.md":
                continue
                
            skill = self._parse_file(file_path)
            if skill:
                skills.append(skill)
                
        return SkillPack(name=pack_name, skills=skills)

    def _parse_file(self, file_path: Path) -> Optional[Skill]:
        content = file_path.read_text(encoding='utf-8')
        
        # Extract frontmatter
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            return None
            
        try:
            fm = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError:
            return None
            
        description = fm.get('description', '')
        globs = fm.get('globs', [])
        
        # Use filename as skill name if not present (slight deviation but useful)
        name = file_path.stem
        
        return Skill(
            name=name,
            description=description,
            category="project_rules", # Generic category for imported rules
            triggers=globs, 
            when_to_use=[description], # Use description as when_to_use
            source="agent-rules"
        )

class VercelSkillsImporter(SkillImporter):
    """Imports skills from SKILL.md structure (vercel-labs/agent-skills)."""
    
    def import_skills(self, source_path: Path) -> SkillPack:
        skills = []
        pack_name = source_path.name
        
        # Vercel structure is typically {skill-name}/SKILL.md
        skill_files = list(source_path.glob("**/SKILL.md"))
        
        for file_path in skill_files:
            skill = self._parse_file(file_path)
            if skill:
                skills.append(skill)
                
        return SkillPack(name=pack_name, skills=skills)
        
    def _parse_file(self, file_path: Path) -> Optional[Skill]:
        content = file_path.read_text(encoding='utf-8')
        
        # Vercel skills usually have a simpler structure, often just markdown text.
        # But we need basic metadata. If they follow a specific frontmatter, good.
        # If not, we might need heuristics.
        # Assuming the parent folder name is the skill name.
        name = file_path.parent.name
        
        # Attempt to find description (first paragraph?)
        # For v1, let's keep it simple: take the whole content as usage/instruction
        
        return Skill(
            name=name,
            description=f"Imported skill: {name}",
            category="vercel_skill",
            usage_example=content,
            source="vercel-agent-skills"
        )

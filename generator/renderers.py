import json
import yaml
from typing import List, Dict, Type
from .types import SkillFile

class SkillRenderer:
    def render(self, skill_file: SkillFile) -> str:
        raise NotImplementedError

# Registry for renderers
_RENDERER_REGISTRY: Dict[str, Type[SkillRenderer]] = {}

def register_renderer(format_name: str):
    """Decorator to register a skill renderer"""
    def decorator(cls: Type[SkillRenderer]):
        _RENDERER_REGISTRY[format_name] = cls
        return cls
    return decorator

def get_renderer(format_name: str) -> SkillRenderer:
    """Get a renderer instance for the specified format"""
    renderer_cls = _RENDERER_REGISTRY.get(format_name.lower())
    if not renderer_cls:
        # Fallback to markdown if unknown, or raise error. 
        # Given the previous logic was "else markdown", let's default to markdown but log a warning if we had logging.
        # For now, explicit definitions are better.
        # But to be safe and match previous behavior of "else -> markdown":
        if 'markdown' in _RENDERER_REGISTRY:
             return _RENDERER_REGISTRY['markdown']()
        raise ValueError(f"No renderer found for format: {format_name}")
    return renderer_cls()

@register_renderer('markdown')
class MarkdownSkillRenderer(SkillRenderer):
    def render(self, skill_file: SkillFile) -> str:
        content = f"""---
project: {skill_file.project_name}
purpose: Agent skills for this project
type: agent-skills
detected_type: {skill_file.project_type}
confidence: {skill_file.confidence:.2f}
version: {skill_file.version}
---

## PROJECT CONTEXT
- **Type**: {skill_file.project_type.replace('_', ' ').title()}
- **Tech Stack**: {', '.join(skill_file.tech_stack) if skill_file.tech_stack else 'general'}
- **Domain**: {skill_file.description[:100]}...

"""
        # Group skills by category
        skills_by_cat = {}
        for skill in skill_file.skills:
            if skill.category not in skills_by_cat:
                skills_by_cat[skill.category] = []
            skills_by_cat[skill.category].append(skill)
            
        # Define category order
        cat_order = ['core', 'tech', skill_file.project_type, 'agent', 'general']
        # Deduplicate while preserving order
        cat_order = list(dict.fromkeys(cat_order))
        
        # Add any other categories found
        for cat in skills_by_cat:
            if cat not in cat_order:
                cat_order.append(cat)
                
        for cat in cat_order:
            if cat not in skills_by_cat or not skills_by_cat[cat]:
                continue
                
            heading = cat.upper().replace('_', ' ')
            if cat == skill_file.project_type:
                heading = f"{heading} SKILLS"
            elif cat == 'core' or cat == 'tech':
                heading = f"{heading} SKILLS"
            else:
                heading = f"ADDITIONAL: {heading}"
                
            content += f"## {heading}\n\n"
            
            for skill in skills_by_cat[cat]:
                content += f"### {skill.name}\n"
                content += f"{skill.description}\n\n"
                
                if getattr(skill, 'source', 'project') != 'project':
                    content += f"> *Source: {skill.source}*\n\n"
                
                if skill.tools:
                    content += f"**Tools:** {', '.join(skill.tools)}\n\n"
                
                if skill.triggers:
                    content += "**Triggers:**\n"
                    for t in skill.triggers:
                        content += f"- {t}\n"
                    content += "\n"

                if skill.when_to_use:
                    content += "**When to use:**\n"
                    for w in skill.when_to_use:
                        content += f"- {w}\n"
                    content += "\n"
                    
                if skill.avoid_if:
                    content += "**Avoid if:**\n"
                    for a in skill.avoid_if:
                        content += f"- {a}\n"
                    content += "\n"
                    
                if skill.input_desc:
                    content += f"**Input:** {skill.input_desc}\n"
                if skill.output_desc:
                    content += f"**Output:** {skill.output_desc}\n\n"
                    
                if skill.usage_example:
                    content += "**Usage:**\n"
                    # If usage example is multiline or code, format it
                    if "```" in skill.usage_example:
                        content += f"{skill.usage_example}\n\n"
                    else:
                        content += f"```bash\n{skill.usage_example}\n```\n\n"
                        
        content += """## USAGE

### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from {project}-skills.md

### In OpenClaw
```bash
/skills load {project}-skills.md
```

### Manual Reference
Read this file before working on the project.
"""
        return content.format(project=skill_file.project_name)

@register_renderer('json')
class JsonSkillRenderer(SkillRenderer):
    def render(self, skill_file: SkillFile) -> str:
        data = {
            "meta": {
                "project": skill_file.project_name,
                "type": skill_file.project_type,
                "confidence": skill_file.confidence,
                "tech_stack": skill_file.tech_stack,
                "version": skill_file.version
            },
            "skills": [s.to_dict() for s in skill_file.skills]
        }
        return json.dumps(data, indent=2)

@register_renderer('yaml')
class YamlSkillRenderer(SkillRenderer):
    def render(self, skill_file: SkillFile) -> str:
        data = {
            "meta": {
                "project": skill_file.project_name,
                "type": skill_file.project_type,
                "confidence": skill_file.confidence,
                "tech_stack": skill_file.tech_stack,
                "version": skill_file.version
            },
            "skills": [s.to_dict() for s in skill_file.skills]
        }
        return yaml.dump(data, sort_keys=False)
